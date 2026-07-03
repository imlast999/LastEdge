import { Router } from "express";
import healthRouter from "./health.js";
import { botRouter, getBotStatus } from "./bot.js";
import { researchRouter } from "./research.js";
import { requireAuth } from "../lib/auth.js";

const router = Router();

// Health check — public (no auth required, used by load-balancers / uptime monitors)
router.use(healthRouter);

// Status — public (lectura local; el navegador y la app pueden comprobar conexión)
router.get("/status", getBotStatus);

// Resto de endpoints requieren token
router.use("/", requireAuth, botRouter);
router.use("/research", requireAuth, researchRouter);

export default router;
