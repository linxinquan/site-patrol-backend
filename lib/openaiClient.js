// 共享千问（OpenAI 兼容）客户端。所有路由复用同一把 Key / 同一个模型。
require('dotenv').config();
const OpenAI = require('openai');

const client = new OpenAI({
  apiKey: process.env.DASHSCOPE_API_KEY,
  baseURL: process.env.QWEN_BASE_URL,
});

const MODEL = process.env.QWEN_MODEL || 'qwen3.8-max';

module.exports = { client, MODEL };
