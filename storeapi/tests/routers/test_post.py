import pytest
from httpx import AsyncClient


async def create_post(body: str, async_client: AsyncClient) -> dict:
    response = await async_client.post("/postapi/post", json={"body": body})
    print("inside create post")

    print(response)
    return response.json()


async def create_comment(body: str, post_id: int, async_client: AsyncClient) -> dict:
    response = await async_client.post(
        "/postapi/comment", json={"body": body, "post_id": post_id}
    )
    print("inside create post")

    print(response)
    return response.json()


@pytest.fixture
async def created_post(async_client: AsyncClient):
    print("inside created post")
    return await create_post("Test Post", async_client)


@pytest.fixture
async def created_comment(async_client: AsyncClient):
    print("inside created comment")
    return await create_comment("Test Comment", 0, async_client)


@pytest.mark.anyio
async def test_create_post(async_client: AsyncClient):
    body = "Test Post"

    response = await async_client.post("/postapi/post", json={"body": body})

    assert response.status_code == 201
    assert {"id": 0, "body": body}.items() <= response.json().items()


@pytest.mark.anyio
async def test_create_post_422(async_client: AsyncClient):
    response = await async_client.post("/postapi/post", json={})

    assert response.status_code == 422
    # assert response == "Internal server error"


@pytest.mark.anyio
async def test_get_post_422(async_client: AsyncClient, created_post: dict):
    response = await async_client.get("/postapi/get-posts")

    assert response.status_code == 200
    print(response.json())
    assert response.json() == [created_post]
    # assert response == "Internal server error"


@pytest.mark.anyio
async def test_create_comment(async_client: AsyncClient, created_post: dict):
    body = "Test Comment"
    # post_id = 0

    response = await async_client.post(
        "/postapi/comment", json={"body": body, "post_id": created_post["id"]}
    )

    assert response.status_code == 201
    assert {
        "body": body,
        "id": 0,
        "post_id": created_post["id"],
    }.items() <= response.json().items()


@pytest.mark.anyio
async def test_get_comment_success(
    async_client: AsyncClient, created_post: dict, created_comment: dict
):
    response = await async_client.get(f"postapi/post/{created_post['id']}/comment")

    assert response.status_code == 200
    assert response.json() == [created_comment]


@pytest.mark.anyio
async def test_get_comment_empty(async_client: AsyncClient, created_post: dict):
    response = await async_client.get(f"postapi/post/{created_post['id']}/comment")

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.anyio
async def test_get_post_with_cooment(
    async_client: AsyncClient, created_post: dict, created_comment: dict
):
    response = await async_client.get(f"/postapi/post/{created_post['id']}")

    assert response.status_code == 200
    assert response.json() == {"post": created_post, "comments": [created_comment]}


@pytest.mark.anyio
async def test_get_missing_post_with_cooment(
    async_client: AsyncClient, created_post: dict, created_comment: dict
):
    response = await async_client.get("/postapi/post/2")

    assert response.status_code == 404
