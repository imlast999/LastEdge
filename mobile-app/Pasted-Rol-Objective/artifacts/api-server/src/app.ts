import express from "express";
import cors from "cors";
import { pinoHttp } from "pino-http";
import { logger } from "./lib/logger.js";
import routes from "./routes/index.js";

const app = express();

// ── Logging ───────────────────────────────────────────────────────────────────
app.use(
  pinoHttp({
    logger,
    serializers: {
      req(req) {
        return { id: req.id, method: req.method, url: req.url?.split("?")[0] };
      },
      res(res) {
        return { statusCode: res.statusCode };
      },
    },
  })
);

// ── CORS ──────────────────────────────────────────────────────────────────────
// Restrict to origins listed in ALLOWED_ORIGINS (comma-separated).
// If the env var is not set, fall back to open CORS only in development.
const allowedOrigins = process.env.ALLOWED_ORIGINS
  ? process.env.ALLOWED_ORIGINS.split(",").map((o) => o.trim()).filter(Boolean)
  : [];

const IS_PROD = process.env.NODE_ENV === "production";

app.use(
  cors({
    origin: allowedOrigins.length > 0
      ? allowedOrigins
      : IS_PROD
        ? false          // block all cross-origin in prod if not configured
        : "*",           // allow all in dev for convenience
    methods: ["GET", "POST"],
    allowedHeaders: ["Content-Type", "Authorization"],
  })
);

// ── Body parsing ──────────────────────────────────────────────────────────────
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// ── Routes ────────────────────────────────────────────────────────────────────
app.use("/api", routes);

export default app;
