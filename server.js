require('dotenv').config();
const express = require('express');
const OpenAI = require('openai');

const app = express();
// 允许浏览器跨域访问（Web 前端 localhost:8000 → 本服务）。生产按需收紧 origin。
app.use((req, res, next) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET,POST,OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type,Authorization');
  if (req.method === 'OPTIONS') return res.sendStatus(204);
  next();
});
app.use(express.json({ limit: '5mb' })); // base64 图片体量大，默认 100kb 会 413

const client = new OpenAI({
  apiKey: process.env.DASHSCOPE_API_KEY,
  baseURL: process.env.QWEN_BASE_URL,
});

const MODEL = process.env.QWEN_MODEL || 'qwen3.8-max';

// 默认 prompt：识别缺陷 + 置信度。
// conf 表示模型对该缺陷判断的可信度，范围 0.0~1.0：
//   1.0 = 100% 确定是该缺陷，无需人工复核；
//   0.0 = 模型判断错误或无法判断，必须人工复核；
//   中间值越低越存疑，越需要人工复核。
const DEFAULT_PROMPT =
  '你是工地质量巡检助手。识别图片中的施工缺陷，返回 JSON：{"count": 缺陷数量, "defects": [{"name": 缺陷名称, "desc": 缺陷描述, "conf": 置信度}]}。' +
  'conf 为该缺陷判断的可信度（0.0~1.0 数值）：1.0 表示模型 100% 确定是该缺陷、无需人工复核；0.0 表示模型判断错误或无法判断、必须人工复核；数值越低越存疑、越需要人工复核。' +
  '没有缺陷时 count 为 0，defects 为空数组。';

// 健康检查
app.get('/health', (req, res) => {
  res.json({ ok: true, model: MODEL });
});

// 缺陷识别：POST { image: dataURL 或 http url, prompt? }
app.post('/api/vision', async (req, res) => {
  try {
    const { image, prompt } = req.body;
    if (!image) return res.status(400).json({ error: '缺少 image 字段' });

    const resp = await client.chat.completions.create({
      model: MODEL,
      messages: [
        {
          role: 'user',
          content: [
            { type: 'text', text: prompt || DEFAULT_PROMPT },
            { type: 'image_url', image_url: { url: image } },
          ],
        },
      ],
    });

    res.json({ content: resp.choices[0].message.content });
  } catch (e) {
    console.error('vision error:', e.message);
    res.status(500).json({ error: e.message });
  }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`gongdi vision backend running at http://localhost:${PORT}`);
  console.log(`model: ${MODEL}`);
});
