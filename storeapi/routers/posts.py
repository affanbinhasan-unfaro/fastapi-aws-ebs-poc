from fastapi import APIRouter, HTTPException

from storeapi.models.posts import (
    Comment,
    CommentIn,
    UserPost,
    UserPostIn,
    UserPostWithComments,
)

router = APIRouter()

# database
post_table = {}
comment_table = {}


def find_post(post_id: int):
    return post_table.get(post_id)


@router.get("/")
async def root():
    return {"message": "Hello World"}


@router.post("/post", response_model=UserPost, status_code=201)
async def create_post(post: UserPostIn):
    data = post.dict()
    last_record_id = len(post_table)
    new_post = {**data, "id": last_record_id}
    post_table[last_record_id] = new_post
    return new_post


@router.post("/comment", response_model=Comment, status_code=201)
async def create_comment(comment: CommentIn):
    post = find_post(comment.post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post Not Found")

    data = comment.dict()
    last_record_id = len(comment_table)
    new_comment = {**data, "id": last_record_id}
    comment_table[last_record_id] = new_comment
    return new_comment


@router.get("/post/{post_id}/comment", response_model=list[Comment])
async def get_comment_on_post(post_id: int):
    # list comprehension
    return [
        comment for comment in comment_table.values() if comment["post_id"] == post_id
    ]


@router.get("/post/{post_id}", response_model=UserPostWithComments)
async def get_post_with_comment(post_id: int):
    post = find_post(post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not Found")
    try:
        print(post_id)

        return {
            "post": post,
            "comments": await get_comment_on_post(post_id),
        }
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Error Occurred: {error}")


@router.get("/get-posts", response_model=list[UserPost])
async def get_post():
    return list(post_table.values())


# @router.get("/get-post/{post_id}", response_model=UserPost)
# async def get_post(post_id: int):
#     return post_table[post_id]


async def get_all_posts():
    return list(post_table.values())
