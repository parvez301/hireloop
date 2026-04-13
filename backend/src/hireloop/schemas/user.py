from hireloop.schemas.common import TimestampedORM


class UserResponse(TimestampedORM):
    cognito_sub: str
    email: str
    name: str
