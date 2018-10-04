curl "https://${ZENDESK_SUBDOMAIN}.zendesk.com/api/v2/imports/tickets/create_many.json" \
    -v -u "${ZENDESK_EMAIL}:${ZENDESK_PASSWORD}" -X POST -d "@$1" -H "Content-Type: application/json"
