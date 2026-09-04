# Frontend — Stage 1

## Stack
- React 18 + TypeScript
- Vite
- Tailwind CSS
- React Router v6
- Lucide icons

## Pages
| Route | Page | Description |
|-------|------|-------------|
| /login | Login | Email + password |
| /register | Register | Org name + email + password |
| / | Dashboard | Stats + recent campaigns |
| /campaigns | Campaigns | List all campaigns |
| /campaigns/new | Create Campaign | Natural language input |
| /campaigns/:id | Campaign Detail | Params, start discovery, leads |
| /leads/:id | Lead Detail | Score, stage, create message |
| /approvals | Approval Queue | Approve / reject messages |
| /suppression | Do Not Contact | Manage suppression list |

## Run
```bash
cd frontend
npm install
npm run dev
```
Opens on http://localhost:5173  
API is proxied to http://localhost:8000

## Auth
JWT stored in localStorage as `access_token`.  
All API calls attach `Authorization: Bearer <token>`.
