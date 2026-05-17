from django.db.models import Q
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from smartagile.permissions import IsAdminRole

from .models import Project, Task
from .serializers import (
    AdminTaskSerializer,
    ProjectAdminSerializer,
    ProjectEmployeeSerializer,
    TaskSerializer,
)


class TaskListView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TaskSerializer

    def get_queryset(self):
        uid = self.request.user.pk
        return Task.objects.filter(user_id=uid).select_related("project")

    def perform_create(self, serializer):
        uid = self.request.user.pk
        serializer.save(user_id=uid, created_by_id=uid)


class TaskDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TaskSerializer

    def get_queryset(self):
        uid = self.request.user.pk
        return Task.objects.filter(user_id=uid).select_related("project")


class EmployeeProjectListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ProjectEmployeeSerializer

    def get_queryset(self):
        uid = self.request.user.pk
        return (
            Project.objects.filter(Q(lead_id=uid) | Q(manager_id=uid) | Q(members__user_id=uid))
            .select_related("lead", "manager")
            .prefetch_related("members")
            .distinct()
        )


class AdminProjectListCreateView(APIView):
    permission_classes = [IsAuthenticated, IsAdminRole]

    def get(self, request):
        qs = (
            Project.objects.all()
            .select_related("lead", "manager", "created_by")
            .prefetch_related("members__user")
        )
        return Response(ProjectAdminSerializer(qs, many=True, context={"request": request}).data)

    def post(self, request):
        ser = ProjectAdminSerializer(data=request.data, context={"request": request})
        if ser.is_valid():
            ser.save()
            return Response(
                ProjectAdminSerializer(ser.instance, context={"request": request}).data,
                status=status.HTTP_201_CREATED,
            )
        return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)


class AdminProjectDetailView(APIView):
    permission_classes = [IsAuthenticated, IsAdminRole]

    def get(self, request, pk):
        try:
            p = Project.objects.select_related("lead", "manager").prefetch_related("members__user").get(pk=pk)
        except Project.DoesNotExist:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(ProjectAdminSerializer(p, context={"request": request}).data)

    def patch(self, request, pk):
        try:
            p = Project.objects.get(pk=pk)
        except Project.DoesNotExist:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        ser = ProjectAdminSerializer(p, data=request.data, partial=True, context={"request": request})
        if ser.is_valid():
            ser.save()
            return Response(ProjectAdminSerializer(p, context={"request": request}).data)
        return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        try:
            p = Project.objects.get(pk=pk)
        except Project.DoesNotExist:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        p.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminTaskListCreateView(APIView):
    permission_classes = [IsAuthenticated, IsAdminRole]

    def get(self, request):
        qs = Task.objects.all().select_related("user", "project")
        return Response(AdminTaskSerializer(qs, many=True).data)

    def post(self, request):
        ser = AdminTaskSerializer(data=request.data, context={"request": request})
        if ser.is_valid():
            ser.save()
            return Response(AdminTaskSerializer(ser.instance).data, status=status.HTTP_201_CREATED)
        return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)


class AdminTaskDetailView(APIView):
    permission_classes = [IsAuthenticated, IsAdminRole]

    def get(self, request, pk):
        try:
            t = Task.objects.select_related("user", "project").get(pk=pk)
        except Task.DoesNotExist:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(AdminTaskSerializer(t).data)

    def patch(self, request, pk):
        try:
            t = Task.objects.get(pk=pk)
        except Task.DoesNotExist:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        ser = AdminTaskSerializer(t, data=request.data, partial=True, context={"request": request})
        if ser.is_valid():
            ser.save()
            return Response(AdminTaskSerializer(t).data)
        return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        try:
            t = Task.objects.get(pk=pk)
        except Task.DoesNotExist:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        t.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
