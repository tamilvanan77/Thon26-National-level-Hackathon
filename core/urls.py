from django.urls import path
from . import views

urlpatterns = [
    path('', views.login_view, name='home'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),

    path('dashboard/', views.dashboard, name='dashboard'),
    path('my-profile/', views.my_profile, name='my_profile'),
    path('doctor-profile/', views.doctor_profile, name='doctor_profile'),
    path('patient/<int:id>/', views.patient_profile, name='patient_profile'),
    path('appointment/<int:id>/update/', views.appointment_update, name='appointment_update'),

    path('report/<int:id>/', views.report_view, name='report'),

    path('assistant/', views.chatbot_page, name='chatbot_page'),
    path('chatbot-api/', views.chatbot_api, name='chatbot_api'),
    path('risk-preview/', views.risk_preview_api, name='risk_preview_api'),

    path("drug-check/", views.drug_check_view, name="drug_check"),
    path("visual-diagnosis/", views.visual_diagnosis, name="visual_diagnosis"),
    path("visual-diagnosis/result/<int:pk>/", views.visual_diagnosis_result, name="visual_diagnosis_result"),
    path("ocr-upload/", views.ocr_upload_view, name="ocr_upload"),
    path('patient/<int:id>/verify/', views.verify_prediction, name='verify_prediction'),
]
