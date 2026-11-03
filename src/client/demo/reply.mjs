import { workbenchSuggestions } from '../src/pages/workbench/simpleWorkbenchData.mjs';

export function demoReply(data) {
  const items = workbenchSuggestions(data);
  return `演示回复 · ${data.store_id} / ${data.snapshot_id}\n\n这是虚构数据的预设说明，不连接真实 AI 服务。\n\n${items.map((item, index) => `${index + 1}. ${item.name}：${item.reason}。${item.action}。`).join('\n')}\n\n下一步可查看商品详情并补充处理记录。当前未执行任何平台改价、库存或订单操作。实际工作台会接入你配置的 Agent。`;
}
