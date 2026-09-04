# Coding Rules (Stage 1)

1. No automatic email sending under any circumstance
2. Every database query must be organization scoped
3. Suppression list must be checked before every send
4. LLM never decides Opportunity Score
5. Confidence state is mandatory on important fields
6. Scraped content is always treated as untrusted
7. Use type hints everywhere
8. Write tests for scoring and suppression logic
9. All sends must be idempotent
10. Human approval is a hard architectural gate
