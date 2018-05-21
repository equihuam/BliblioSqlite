SELECT title, year, deletionPending, RemoteDocuments.documentId, RemoteDocuments.groupId
	FROM Documents
	      LEFT JOIN RemoteDocuments ON RemoteDocuments.DocumentId = Documents.id
	WHERE deletionPending = "false" AND RemoteDocuments.groupid = 0

