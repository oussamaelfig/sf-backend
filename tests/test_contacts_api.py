import base64

from app.schemas import MAX_PHOTO_BYTES

BASE = "/api/v1/contacts"

TINY_PNG = (
    "data:image/png;base64,"
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "sqlite"


def test_create_contact(client, payload):
    response = client.post(BASE, json=payload)
    assert response.status_code == 201
    body = response.json()
    assert body["id"] > 0
    assert body["email"] == "ada@example.com"
    assert body["full_name"] == "Ada Lovelace"
    assert body["created_at"] and body["updated_at"]


def test_create_requires_valid_email(client, payload):
    response = client.post(BASE, json={**payload, "email": "not-an-email"})
    assert response.status_code == 422


def test_create_requires_names(client, payload):
    response = client.post(BASE, json={**payload, "first_name": ""})
    assert response.status_code == 422


def test_duplicate_email_conflicts(client, payload):
    assert client.post(BASE, json=payload).status_code == 201
    response = client.post(BASE, json={**payload, "email": "ADA@example.com"})
    assert response.status_code == 409


def test_get_contact(client, payload):
    contact_id = client.post(BASE, json=payload).json()["id"]
    response = client.get(f"{BASE}/{contact_id}")
    assert response.status_code == 200
    assert response.json()["id"] == contact_id


def test_get_missing_contact_returns_404(client):
    assert client.get(f"{BASE}/9999").status_code == 404


def test_list_pagination_and_total(client, payload):
    for index in range(5):
        client.post(BASE, json={**payload, "email": f"user{index}@example.com"})

    response = client.get(BASE, params={"limit": 2, "offset": 2})
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 5
    assert len(body["items"]) == 2
    assert body["limit"] == 2 and body["offset"] == 2


def test_list_search(client, payload):
    client.post(BASE, json=payload)
    client.post(
        BASE,
        json={**payload, "first_name": "Grace", "last_name": "Hopper", "email": "grace@example.com", "company": "US Navy"},
    )

    hits = client.get(BASE, params={"search": "hopper"}).json()
    assert hits["total"] == 1
    assert hits["items"][0]["last_name"] == "Hopper"

    by_company = client.get(BASE, params={"search": "navy"}).json()
    assert by_company["total"] == 1

    misses = client.get(BASE, params={"search": "nobody"}).json()
    assert misses["total"] == 0


def test_list_sorting(client, payload):
    client.post(BASE, json={**payload, "last_name": "Zhang", "email": "z@example.com"})
    client.post(BASE, json={**payload, "last_name": "Adams", "email": "a@example.com"})

    names = [
        item["last_name"]
        for item in client.get(BASE, params={"sort_by": "last_name", "order": "asc"}).json()["items"]
    ]
    assert names == ["Adams", "Zhang"]


def test_list_rejects_bad_sort_field(client):
    assert client.get(BASE, params={"sort_by": "; DROP TABLE contacts"}).status_code == 422


def test_patch_updates_only_sent_fields(client, payload):
    contact_id = client.post(BASE, json=payload).json()["id"]
    response = client.patch(f"{BASE}/{contact_id}", json={"phone": "+1-000-000-0000"})
    assert response.status_code == 200
    body = response.json()
    assert body["phone"] == "+1-000-000-0000"
    assert body["first_name"] == "Ada"
    assert body["company"] == "Analytical Engines"


def test_patch_duplicate_email_conflicts(client, payload):
    first = client.post(BASE, json=payload).json()["id"]
    client.post(BASE, json={**payload, "email": "grace@example.com"})
    response = client.patch(f"{BASE}/{first}", json={"email": "grace@example.com"})
    assert response.status_code == 409


def test_patch_same_email_is_allowed(client, payload):
    contact_id = client.post(BASE, json=payload).json()["id"]
    response = client.patch(f"{BASE}/{contact_id}", json={"email": payload["email"]})
    assert response.status_code == 200


def test_put_replaces_contact(client, payload):
    contact_id = client.post(BASE, json=payload).json()["id"]
    response = client.put(
        f"{BASE}/{contact_id}",
        json={"first_name": "Grace", "last_name": "Hopper", "email": "grace@example.com"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["full_name"] == "Grace Hopper"
    assert body["company"] is None  # omitted fields are cleared by PUT


def test_put_missing_contact_returns_404(client):
    response = client.put(
        f"{BASE}/9999",
        json={"first_name": "A", "last_name": "B", "email": "ab@example.com"},
    )
    assert response.status_code == 404


def test_delete_contact(client, payload):
    contact_id = client.post(BASE, json=payload).json()["id"]
    assert client.delete(f"{BASE}/{contact_id}").status_code == 204
    assert client.get(f"{BASE}/{contact_id}").status_code == 404
    assert client.delete(f"{BASE}/{contact_id}").status_code == 404


def test_root_lists_entrypoints(client):
    body = client.get("/").json()
    assert body["contacts"] == BASE


def test_create_contact_with_photo(client, payload):
    response = client.post(BASE, json={**payload, "photo": TINY_PNG})
    assert response.status_code == 201
    assert response.json()["photo"] == TINY_PNG


def test_photo_defaults_to_none(client, payload):
    response = client.post(BASE, json=payload)
    assert response.status_code == 201
    assert response.json()["photo"] is None


def test_photo_rejects_plain_url(client, payload):
    response = client.post(BASE, json={**payload, "photo": "https://example.com/ada.png"})
    assert response.status_code == 422


def test_photo_rejects_unsupported_mime_type(client, payload):
    svg = "data:image/svg+xml;base64,PHN2Zz48L3N2Zz4="
    response = client.post(BASE, json={**payload, "photo": svg})
    assert response.status_code == 422


def test_photo_rejects_invalid_base64(client, payload):
    response = client.post(BASE, json={**payload, "photo": "data:image/png;base64,%%%not-base64%%%"})
    assert response.status_code == 422


def test_photo_rejects_oversized_payload(client, payload):
    too_big = "data:image/png;base64," + base64.b64encode(b"x" * (MAX_PHOTO_BYTES + 1)).decode()
    response = client.post(BASE, json={**payload, "photo": too_big})
    assert response.status_code == 422


def test_patch_preserves_photo(client, payload):
    contact_id = client.post(BASE, json={**payload, "photo": TINY_PNG}).json()["id"]
    response = client.patch(f"{BASE}/{contact_id}", json={"phone": "+1-000-000-0000"})
    assert response.status_code == 200
    assert response.json()["photo"] == TINY_PNG


def test_patch_with_null_clears_photo(client, payload):
    contact_id = client.post(BASE, json={**payload, "photo": TINY_PNG}).json()["id"]
    response = client.patch(f"{BASE}/{contact_id}", json={"photo": None})
    assert response.status_code == 200
    assert response.json()["photo"] is None


def test_put_carries_photo_through(client, payload):
    contact_id = client.post(BASE, json={**payload, "photo": TINY_PNG}).json()["id"]
    response = client.put(f"{BASE}/{contact_id}", json={**payload, "photo": TINY_PNG})
    assert response.status_code == 200
    assert response.json()["photo"] == TINY_PNG


def test_read_schema_skips_photo_validation():
    # Serialization must not re-decode stored photos (they were validated on
    # write); ContactRead therefore accepts values the input schemas reject.
    from datetime import datetime, timezone

    from app.schemas import ContactRead

    read = ContactRead.model_validate(
        {
            "id": 1,
            "first_name": "Ada",
            "last_name": "Lovelace",
            "email": "ada@example.com",
            "photo": "data:image/gif;base64,unvalidated-on-read",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
    )
    assert read.photo == "data:image/gif;base64,unvalidated-on-read"


def test_put_without_photo_clears_it(client, payload):
    # PUT is a full replace: clients (like the edit form) must echo the photo
    # back or it is intentionally cleared, consistent with every other field.
    contact_id = client.post(BASE, json={**payload, "photo": TINY_PNG}).json()["id"]
    response = client.put(f"{BASE}/{contact_id}", json=payload)
    assert response.status_code == 200
    assert response.json()["photo"] is None


def test_create_contact_with_addresses(client, payload):
    response = client.post(BASE, json=payload)
    assert response.status_code == 201
    addresses = response.json()["addresses"]
    assert [a["type"] for a in addresses] == ["Home", "Work"]
    assert all(a["id"] > 0 for a in addresses)
    assert addresses[1]["street"] == "1 Market St, Suite 400"


def test_addresses_default_to_empty_list(client, payload):
    slim = {k: v for k, v in payload.items() if k != "addresses"}
    response = client.post(BASE, json=slim)
    assert response.status_code == 201
    assert response.json()["addresses"] == []


def test_address_type_is_validated(client, payload):
    bad = {**payload, "addresses": [{"type": "Vacation", "street": "1 Beach Rd"}]}
    assert client.post(BASE, json=bad).status_code == 422


def test_address_count_is_capped_at_ten(client, payload):
    eleven = [{"type": "Home", "city": f"City {i}"} for i in range(11)]
    response = client.post(BASE, json={**payload, "addresses": eleven})
    assert response.status_code == 422

    # Exactly ten is still fine — the cap is inclusive.
    ten = eleven[:10]
    assert client.post(BASE, json={**payload, "addresses": ten}).status_code == 201


def test_put_replaces_the_whole_address_set(client, payload):
    contact_id = client.post(BASE, json=payload).json()["id"]
    replacement = {**payload, "addresses": [{"type": "Other", "street": "99 New St"}]}
    response = client.put(f"{BASE}/{contact_id}", json=replacement)
    assert response.status_code == 200
    addresses = response.json()["addresses"]
    assert [(a["type"], a["street"]) for a in addresses] == [("Other", "99 New St")]


def test_patch_omitting_addresses_keeps_them(client, payload):
    contact_id = client.post(BASE, json=payload).json()["id"]
    response = client.patch(f"{BASE}/{contact_id}", json={"phone": "+1-999-000-0000"})
    assert response.status_code == 200
    assert len(response.json()["addresses"]) == 2


def test_patch_with_empty_list_clears_addresses(client, payload):
    contact_id = client.post(BASE, json=payload).json()["id"]
    response = client.patch(f"{BASE}/{contact_id}", json={"addresses": []})
    assert response.status_code == 200
    assert response.json()["addresses"] == []


def test_deleting_contact_deletes_its_addresses(client, payload):
    contact_id = client.post(BASE, json=payload).json()["id"]
    assert client.delete(f"{BASE}/{contact_id}").status_code == 204
    # Re-registering the same person starts from a clean slate: no orphaned
    # rows resurface through the relationship.
    recreated = client.post(BASE, json={**payload, "addresses": []}).json()
    assert recreated["addresses"] == []
