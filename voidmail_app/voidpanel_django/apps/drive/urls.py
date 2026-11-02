from django.urls import path
from . import views

urlpatterns = [
    # Main listing & upload
    path('api/files/', views.get_drive_files_api, name='drive_files_api'),
    path('api/upload/', views.upload_drive_file_api, name='drive_upload_api'),
    path('api/download/<int:file_id>/', views.download_drive_file_api, name='drive_download_api'),
    
    # Folder management
    path('api/folders/create/', views.create_folder_api, name='drive_create_folder_api'),
    path('api/folders/color/', views.update_folder_color_api, name='drive_folder_color_api'),
    
    # File & Folder Lifecycle
    path('api/rename/', views.rename_item_api, name='drive_rename_item_api'),
    path('api/star/', views.toggle_star_api, name='drive_toggle_star_api'),
    path('api/trash/', views.trash_item_api, name='drive_trash_item_api'),
    path('api/restore/', views.restore_item_api, name='drive_restore_item_api'),
    path('api/empty-trash/', views.empty_trash_api, name='drive_empty_trash_api'),
    path('api/permanent-delete/', views.permanent_delete_api, name='drive_permanent_delete_api'),
    path('api/delete/', views.permanent_delete_api, name='drive_delete_api'),
    
    # Content Read & Save (Google Docs & Google Sheets)
    path('api/file/content/<int:file_id>/', views.get_file_content_api, name='drive_file_content_api'),
    path('api/file/save/', views.save_file_content_api, name='drive_file_save_api'),
    path('api/create-doc/', views.create_doc_or_sheet_api, name='drive_create_doc_api'),
    
    # Sharing & Permissions (Google Drive 1:1)
    path('api/toggle-share/', views.toggle_share_link_api, name='drive_toggle_share_api'),
    path('api/share-info/<int:file_id>/', views.get_file_share_info_api, name='drive_share_info_api'),
    path('api/update-share/', views.update_share_access_api, name='drive_update_share_api'),
    path('api/public-save/<str:token>/', views.public_save_file_content_api, name='drive_public_save_api'),
    path('share/<str:token>/', views.share_file_view, name='drive_public_share'),
]
