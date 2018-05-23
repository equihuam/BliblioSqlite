SELECT RemoteDocuments.documentId, RemoteDocuments.remoteUuid, DocumentFiles.remoteFileUuid, Documents.title, Documents.note
FROM RemoteDocuments 
LEFT JOIN DocumentFiles ON RemoteDocuments.documentId = DocumentFiles.documentId
LEFT JOIN Documents ON Documents.id = RemoteDocuments.documentId
WHERE DocumentFiles.remoteFileUuid = "";
