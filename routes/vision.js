// 视觉识别路由：POST /api/vision
// body: { image: dataURL 或 http url, prompt?: 自定义指令, project?: 调用方标识 }
const express = require('express');
const router = express.Router();
const { client, MODEL } = require('../lib/openaiClient');

// 默认 prompt（工地缺陷识别，作为兜底；各项目应显式传 prompt 覆盖）。
// conf 表示模型对该缺陷判断的可信度，范围 0.0~1.0：
//   1.0 = 100% 确定是该缺陷，无需人工复核；
//   0.0 = 模型判断错误或无法判断，必须人工复核；
//   中间值越低越存疑，越需要人工复核。
const DEFAULT_PROMPT =
  '你是工地质量巡检助手。识别图片中的施工缺陷，返回 JSON：{"count": 缺陷数量, "defects": [{"name": 缺陷名称, "desc": 缺陷描述, "conf": 置信度}]}。' +
  'conf 为该缺陷判断的可信度（0.0~1.0 数值）：1.0 表示模型 100% 确定是该缺陷、无需人工复核；0.0 表示模型判断错误或无法判断、必须人工复核；数值越低越存疑、越需要人工复核。' +
  '没有缺陷时 count 为 0，defects 为空数组。';

router.post('/', async (req, res) => {
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

module.exports = router;
