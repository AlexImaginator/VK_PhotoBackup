from VKPhotoBackup import VKPhotoBackup


VK_ID = ''
VK_API_TOKEN = ''
YA_DISC_API_TOKEN = ''
backup = VKPhotoBackup(VK_ID, VK_API_TOKEN, YA_DISC_API_TOKEN)
backup.backup_photos()
