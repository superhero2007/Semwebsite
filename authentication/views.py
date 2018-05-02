from django.contrib.auth import authenticate, login, logout
from rest_framework.response import Response
from rest_framework.views import APIView


class UserView(APIView):

    def post(self, request, format=None):
        context = {}
        username = request.data['username']
        password = request.data['password']
        user = authenticate(username=username, password=password)
        if user is not None:
            if user.is_active:
                login(request, user)
                context = {"status": "success", "success": "Success"}
            else:
                context = {"status": "error", "error_message": "The password is valid, but account has been disabled!"}
        else:
            context = {"status": "error", "error_message": "The username and password were incorrect."}

        return Response(context)

    def delete(self, request, format=None):
        status = logout(request)
        return Response(status)


class ChangeView(APIView):

    def put(self, request, format=None):
        context = {}
        username = request.data['username']
        oldPassword = request.data['oldPassword']
        newPassword = request.data['newPassword']
        user = authenticate(username=username, password=oldPassword)
        if user is not None:
            user.set_password(newPassword)
            user.save()
            context = {"status": "success", "success": "Success"}
        else:
            context = {"status": "error", "error_message": "The old password was incorrect."}

        return Response(context)
