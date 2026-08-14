// 通用文本对话路由：POST /api/chat
// body 二选一：
//   1) { messages: [{role, content}, ...] }  —— 完整多轮消息
//   2) { prompt: "..." }                      —— 单轮提问
// 可选 { project?: 调用方标识 } 仅用于日志。
const express = require('express');
const router = express.Router();
const { client, MODEL } = require('../lib/openaiClient');

router.post('/', async (req, res) => {
  try {
    const { messages, prompt } = req.body;
    const msgs =
      Array.isArray(messages) && messages.length
        ? messages
        : [{ role: 'user', content: prompt || '你好' }];

    const resp = await client.chat.completions.create({
      model: MODEL,
      messages: msgs,
    });

    res.json({ content: resp.choices[0].message.content });
  } catch (e) {
    console.error('chat error:', e.message);
    res.status(500).json({ error: e.message });
  }
});

module.exports = router;
