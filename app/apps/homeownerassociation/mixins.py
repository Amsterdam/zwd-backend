from rest_framework.decorators import action
from rest_framework.response import Response
from apps.homeownerassociation.models import HomeownerAssociation, Contact
from apps.homeownerassociation.serializers import HomeownerAssociationSerializer
from .serializers import ContactSerializer
from rest_framework import status


class HomeownerAssociationMixin:
    @action(
        detail=True,
        methods=["get"],
        url_path="homeowner-association",
        serializer_class=HomeownerAssociationSerializer,
    )
    def get_by_bag_id(self, request, pk=None):
        hoa_instance = HomeownerAssociation()
        model = hoa_instance.get_or_create_hoa_by_bag_id(pk)
        serializer = HomeownerAssociationSerializer(model)
        return Response(serializer.data)


class ContactMixin:
    def get_hoa_contacts(self, request, pk=None):
        contacts = self.get_object().contacts.all()
        serializer = ContactSerializer(contacts, many=True)
        return Response(serializer.data)

    def create_or_update_hoa_contacts(self, request, pk=None):
        hoa = self.get_object()
        contacts_data = request.data.get("contacts", [])
        if not contacts_data:
            return Response(
                {"detail": "At least one contact is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        Contact.process_contacts(hoa, contacts_data)
        return Response(
            {"detail": "Contacts added successfully"}, status=status.HTTP_201_CREATED
        )

    @action(
        detail=True,
        url_path="contacts",
        methods=["get", "put"],
    )
    def contacts(self, request, pk=None):
        if request.method == "GET":
            return self.get_hoa_contacts(request, pk)
        elif request.method == "PUT":
            return self.create_or_update_hoa_contacts(request, pk)

    @action(
        detail=True,
        url_path="delete-contact/(?P<contact_id>[^/.]+)",
        methods=["delete"],
    )
    def delete(self, request, pk=None, contact_id=None):
        hoa = self.get_object()
        contact = Contact.objects.get(id=contact_id)
        if len(contact.homeowner_associations.all()) == 1:
            contact.delete()
        else:
            contact.homeowner_associations.remove(hoa)
        return Response(
            "Successfully deleted contact", status=status.HTTP_204_NO_CONTENT
        )
