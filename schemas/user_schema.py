from pydantic import BaseModel
from pydantic_extra_types.isbn import *

class UserResponse(BaseModel):
    user_id: str
    first_name: str
    last_name: str
    email: str
    emailVerified: bool