// 通用 AI 网关（多项目共用）
// 路由：
//   GET  /health           健康检查
//   POST /api/vision       视觉识别（图片 + 可选 prompt）
//   POST /api/chat         通用文本对话
require('dotenv').config();
const express = require('express');
const { MODEL } = require('./lib/openaiClient');
const visionRouter = require('./routes/vision');
const chatRouter = require('./routes/chat');

const app = express();

// ---- CORS 白名单（多项目共用，禁止 *，避免接口被任意网站调用）----
const allowedOrigins = (process.env.ALLOWED_ORIGINS || '')
  .split(',')
  .map((s) => s.trim())
  .filter(Boolean);

if (!allowedOrigins.length) {
  console.warn('[CORS] ALLOWED_ORIGINS 未配置，暂允许所有来源（生产环境请配置白名单）');
}

app.use((req, res, next) => {
  const origin = req.headers.origin;
  // 放行条件：未配置白名单（开发） / 无 origin（服务端或 App 调用，如 Flutter） / origin 在白名单内
  const permit = !allowedOrigins.length || !origin || allowedOrigins.includes(origin);
  if (!permit) {
    return res.status(403).json({ error: 'origin not allowed' });
  }
  if (origin) res.setHeader('Access-Control-Allow-Origin', origin); // 反射具体 origin，优于 *
  res.setHeader('Access-Control-Allow-Methods', 'GET,POST,OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type,Authorization');
  if (req.method === 'OPTIONS') return res.sendStatus(204);
  next();
});

// ---- 调用日志（多项目共用，排查限流/来源）----
app.use((req, res, next) => {
  const start = Date.now();
  res.on('finish', () => {
    const ms = Date.now() - start;
    const project = (req.body && req.body.project) || '-';
    console.log(
      `[${new Date().toISOString()}] ${req.method} ${req.path} project=${project} status=${res.statusCode} ${ms}ms`
    );
  });
  next();
});

app.use(express.json({ limit: '5mb' })); // base64 图片体量大，默认 100kb 会 413

// 健康检查
app.get('/health', (req, res) => {
  res.json({ ok: true, model: MODEL });
});

// 业务路由
app.use('/api/vision', visionRouter);
app.use('/api/chat', chatRouter);

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`AI gateway running at http://localhost:${PORT}`);
  console.log(`model: ${MODEL}`);
});
