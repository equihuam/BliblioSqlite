SELECT Documents.id, COUNT(*) as entries, LOWER(title) as title, year, RemoteDocuments.groupId as gr, Groups.name as gr_name
FROM Documents
	LEFT JOIN RemoteDocuments ON RemoteDocuments.documentId = Documents.id 
	JOIN Groups ON RemoteDocuments.groupId = Groups.id
WHERE DeletionPending = 'false'
GROUP BY title, year, gr HAVING entries > 1 AND gr = 0
ORDER BY entries DESC ;
