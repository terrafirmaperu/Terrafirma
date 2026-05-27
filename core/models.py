# TODO: Consider adding soft delete functionality to BaseModel
# TODO: Add validation for user_creation and user_updated to ensure they are set correctly
# TODO: Implement audit logging for all model changes
# modelo de sistema inicial
from django.db import models
from config import settings as setting


class BaseModel(models.Model):
    user_creation = models.ForeignKey(setting.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True,
                                      related_name='%(app_label)s_%(class)s_creation')
    date_creation = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    user_updated = models.ForeignKey(setting.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True,
                                     related_name='%(app_label)s_%(class)s_updated')
    date_updated = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        abstract = True
