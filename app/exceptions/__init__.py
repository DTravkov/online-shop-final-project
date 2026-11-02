class RecordNotFound(Exception):
    def __init__(self, entity: str, record_id: int):
        super().__init__(f"{entity} {record_id} not found")


class RecordConflict(Exception):
    pass


class UserNotFound(Exception):
    def __init__(self, user_id: int):
        super().__init__(f"User {user_id} not found")
