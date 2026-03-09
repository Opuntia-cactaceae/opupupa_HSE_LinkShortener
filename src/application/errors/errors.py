class ApplicationError(Exception):
    def __init__(self, *args, **kwargs):
        super().__init__(*args)
        for key, value in kwargs.items():
            setattr(self, key, value)


class LinkNotFoundError(ApplicationError):
    pass


class LinkExpiredError(ApplicationError):
    pass


class LinkNotAvailableError(ApplicationError):
    pass


class ShortCodeAlreadyExistsError(ApplicationError):
    pass


class UserNotAuthorizedError(ApplicationError):
    pass


class UserNotFoundError(ApplicationError):
    pass


class InvalidCredentialsError(ApplicationError):
    pass


class EmailAlreadyExistsError(ApplicationError):
    pass


class ProjectNotFoundError(ApplicationError):
    pass


class ProjectAlreadyExistsError(ApplicationError):
    pass


class ValidationError(ApplicationError):
    pass