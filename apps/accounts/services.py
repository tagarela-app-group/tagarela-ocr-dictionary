class AccountService:
    def update(self, user, data: dict):
        for field, value in data.items():
            setattr(user, field, value)
        user.save(update_fields=list(data))

        return user
