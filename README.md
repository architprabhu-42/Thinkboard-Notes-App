<h1 align="center">📝 MERN Stack Note Taking App ✨</h1>

Highlights:

- 🧱 Full-Stack App Built with the MERN Stack (MongoDB, Express, React, Node)
- ✨ Create, Update, and Delete Notes with Title & Description
- 🛠️ Build and Test a Fully Functional REST API
- ⚙️ Rate Limiting with Upstash Redis — a Real-World Concept Explained Simply
- 🚀 Completely Responsive UI
- 🌐 Explore HTTP Methods, Status Codes & SQL vs NoSQL
- 📦 Deployment Guide Included — Add the Live App to Your Resume
- 📚 Designed for Absolute Beginners

---

## 🧪 .env Setup

### Backend (`/backend`)

```
MONGO_URI=<your_mongo_uri>

UPSTASH_REDIS_REST_URL=<your_redis_rest_url>
UPSTASH_REDIS_REST_TOKEN=<your_redis_rest_token>

NODE_ENV=development
```

## 🔧 Run the Backend

```
cd backend
npm install
npm run dev
```

## 💻 Run the Frontend

```
cd frontend
npm install
npm run dev
```

## 🚀 Deploy on Render

This repository includes a Render Blueprint for a single web service that builds the React frontend and serves it from the Express backend. In Render, choose **New → Blueprint**, connect this repository, and deploy `render.yaml`.

Set these environment variables for the service using your own credentials:

- `MONGO_URI`
- `UPSTASH_REDIS_REST_URL`
- `UPSTASH_REDIS_REST_TOKEN`

The Blueprint sets `NODE_ENV=production`. Keep these credentials in Render's environment settings; do not commit them to this repository.
