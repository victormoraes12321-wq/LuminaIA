from __future__ import annotations


class UserProfileError(Exception):
    code = "USER_PROFILE_ERROR"
    http_status = 400

    def __init__(
        self,
        message: str,
        *,
        details: dict[str, str | int | bool] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


def _error(name: str, code: str, status: int):
    return type(name, (UserProfileError,), {"code": code, "http_status": status})


UserProfileNotFoundError = _error("UserProfileNotFoundError", "USER_PROFILE_NOT_FOUND", 404)
UserProfileAccessDeniedError = _error("UserProfileAccessDeniedError", "USER_PROFILE_ACCESS_DENIED", 403)
UserProfileTenantMismatchError = _error("UserProfileTenantMismatchError", "USER_PROFILE_TENANT_MISMATCH", 403)
UserProfileUserMismatchError = _error("UserProfileUserMismatchError", "USER_PROFILE_USER_MISMATCH", 403)
UserProfileVersionConflictError = _error("UserProfileVersionConflictError", "USER_PROFILE_VERSION_CONFLICT", 409)
UserProfileDisabledError = _error("UserProfileDisabledError", "USER_PROFILE_DISABLED", 409)
UserPreferenceNotFoundError = _error("UserPreferenceNotFoundError", "USER_PREFERENCE_NOT_FOUND", 404)
UserPreferenceInvalidError = _error("UserPreferenceInvalidError", "USER_PREFERENCE_INVALID", 422)
UserPreferenceForbiddenError = _error("UserPreferenceForbiddenError", "USER_PREFERENCE_FORBIDDEN", 403)
UserPreferenceConsentRequiredError = _error("UserPreferenceConsentRequiredError", "USER_PREFERENCE_CONSENT_REQUIRED", 409)
UserPreferenceReferenceInvalidError = _error("UserPreferenceReferenceInvalidError", "USER_PREFERENCE_REFERENCE_INVALID", 422)
UserPreferenceAmbiguousError = _error("UserPreferenceAmbiguousError", "USER_PREFERENCE_AMBIGUOUS", 409)
UserPreferenceExpiredError = _error("UserPreferenceExpiredError", "USER_PREFERENCE_EXPIRED", 409)
UserPreferenceConflictError = _error("UserPreferenceConflictError", "USER_PREFERENCE_CONFLICT", 409)
UserProfileExportForbiddenError = _error("UserProfileExportForbiddenError", "USER_PROFILE_EXPORT_FORBIDDEN", 403)
UserProfileImportInvalidError = _error("UserProfileImportInvalidError", "USER_PROFILE_IMPORT_INVALID", 422)
UserProfileDeletionConflictError = _error("UserProfileDeletionConflictError", "USER_PROFILE_DELETION_CONFLICT", 409)
UserProfilePayloadTooLargeError = _error("UserProfilePayloadTooLargeError", "USER_PROFILE_PAYLOAD_TOO_LARGE", 413)
UserProfileFeatureDisabledError = _error("UserProfileFeatureDisabledError", "USER_PROFILE_FEATURE_DISABLED", 503)
