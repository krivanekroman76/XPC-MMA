from rest_framework.decorators import api_view
from rest_framework.response import Response

from .serializers import NoteSerializer
from .models import Note

@api_view(['GET'])
def getRoutes(request):
    routes = [
        {
            'Endpoint': '/notes/',
            'method': 'GET',
            'body': None,
            'description': 'Returns an array of all existing notes'
        },
        {
            'Endpoint': '/notes/id/',
            'method': 'GET',
            'body': None,
            'description': 'Returns a single note object'
        },
        {
            'Endpoint': '/notes/',
            'method': 'POST',
            'body': {'body': ""},
            'description': 'Creates a new note with the data sent in the request body'
        },
        {
            'Endpoint': '/notes/id/',
            'method': 'PUT',
            'body': {'body': ""},
            'description': 'Updates an existing note based on the provided ID'
        },
        {
            'Endpoint': '/notes/id/',
            'method': 'DELETE',
            'body': None,
            'description': 'Deletes a specific note from the database'
        },
    ]
    
    return Response(routes)

from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Note
from .serializers import NoteSerializer

@api_view(['GET', 'POST'])
def getNotes(request):
    if request.method == 'GET':
        notes = Note.objects.all().order_by('-updated')
        serializer = NoteSerializer(notes, many=True)
        return Response(serializer.data)

    if request.method == 'POST':
        # Let the serializer handle the data
        serializer = NoteSerializer(data=request.data)
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=201)
        
        # If invalid, this returns WHY (e.g., {"body": ["This field is required."]})
        return Response(serializer.errors, status=400)


@api_view(['GET', 'PUT', 'DELETE'])
def getNote(request, pk):
    try:
        note = Note.objects.get(id=pk)
    except Note.DoesNotExist:
        return Response({'error': 'Note not found'}, status=404)

    # GET: Show specific note
    if request.method == 'GET':
        serializer = NoteSerializer(note, many=False)
        return Response(serializer.data)

    # PUT: Update specific note
    if request.method == 'PUT':
        data = request.data
        serializer = NoteSerializer(instance=note, data=data)
        if serializer.is_valid():
            serializer.save()
        return Response(serializer.data)

    # DELETE: Delete input from database
    if request.method == 'DELETE':
        note.delete()
        return Response('Note was deleted!')