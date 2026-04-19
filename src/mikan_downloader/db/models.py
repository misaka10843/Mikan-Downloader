from tortoise import fields, models

class DownloadHistory(models.Model):
    guid = fields.CharField(max_length=255, pk=True)
    source = fields.TextField()
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "guids"

class Notification(models.Model):
    id = fields.IntField(pk=True)
    level = fields.CharField(max_length=20) # info, success, warning, error
    title = fields.CharField(max_length=255)
    message = fields.TextField()
    timestamp = fields.DatetimeField(auto_now_add=True)
    is_read = fields.BooleanField(default=False)

    class Meta:
        table = "notifications"

class SystemConfig(models.Model):
    key = fields.CharField(max_length=100, pk=True)
    value = fields.TextField()

    class Meta:
        table = "system_config"

class Subscription(models.Model):
    id = fields.IntField(pk=True)
    url = fields.TextField()
    rule = fields.CharField(max_length=255, default=".*")
    rename_rule = fields.CharField(max_length=255, default="auto")
    date = fields.CharField(max_length=10, null=True)
    title = fields.CharField(max_length=255, null=True)
    cover = fields.TextField(null=True)
    is_deleted = fields.BooleanField(default=False)

    class Meta:
        table = "subscriptions"

class TaskLog(models.Model):
    id = fields.IntField(pk=True)
    job_id = fields.CharField(max_length=100, unique=True)
    last_run = fields.DatetimeField(null=True)
    status = fields.CharField(max_length=20, default="unknown")
    message = fields.TextField(null=True)

    class Meta:
        table = "task_logs"
