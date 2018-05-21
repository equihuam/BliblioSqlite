SELECT Documents.id, title, firstNames, lastName
FROM Documents
	LEFT JOIN DocumentContributors ON DocumentContributors.DocumentId = Documents.id
WHERE deletionPending = "false"

