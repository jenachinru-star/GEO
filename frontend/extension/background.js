// GEO数字资产助手 - Background Service Worker
// 处理后台任务、右键菜单、消息转发

// 安装时初始化右键菜单
chrome.runtime.onInstalled.addListener(() => {
  // 创建右键菜单
  chrome.contextMenus.create({
    id: 'geo-save-page',
    title: '收藏到GEO数字资产库',
    contexts: ['page', 'selection', 'link'],
  });

  chrome.contextMenus.create({
    id: 'geo-save-selection',
    title: '收藏选中内容到GEO',
    contexts: ['selection'],
  });
});

// 右键菜单点击处理
chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (info.menuItemId === 'geo-save-page') {
    await savePage(tab);
  } else if (info.menuItemId === 'geo-save-selection') {
    await saveSelection(tab, info.selectionText);
  }
});

// 保存整个页面
async function savePage(tab) {
  const config = await chrome.storage.sync.get(['apiBase']);
  const apiBase = config.apiBase || 'http://10.16.190.100:8028/geo/api/v1';

  try {
    await fetch(`${apiBase}/asset/sources`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        source_type: 'url',
        title: tab.title,
        url: tab.url,
        source_site: new URL(tab.url).hostname,
        category: 'medicine',
      }),
    });

    // 显示通知
    chrome.notifications?.create({
      type: 'basic',
      iconUrl: 'icons/icon48.png',
      title: 'GEO数字资产',
      message: '网页收藏成功！',
    });
  } catch (e) {
    console.error('收藏失败:', e);
  }
}

// 保存选中内容
async function saveSelection(tab, selectionText) {
  const config = await chrome.storage.sync.get(['apiBase']);
  const apiBase = config.apiBase || 'http://10.16.190.100:8028/geo/api/v1';

  try {
    await fetch(`${apiBase}/asset/sources`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        source_type: 'clipboard',
        title: tab.title + ' - 选中内容',
        url: tab.url,
        source_site: new URL(tab.url).hostname,
        content: selectionText,
        category: 'personal',
      }),
    });
  } catch (e) {
    console.error('收藏失败:', e);
  }
}

// 监听来自popup的消息（预留）
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'getStorage') {
    chrome.storage.sync.get(request.keys || [], (data) => {
      sendResponse(data);
    });
    return true; // 异步响应
  }
});
