// GEO数字资产助手 - Popup逻辑

const $ = (id) => document.getElementById(id);

// 默认配置
const DEFAULT_API_BASE = 'http://10.16.190.100:8028/geo/api/v1';

// 初始化
document.addEventListener('DOMContentLoaded', async () => {
  // 加载API配置
  const config = await chrome.storage.sync.get(['apiBase']);
  $('apiBase').value = config.apiBase || DEFAULT_API_BASE;

  // 获取当前页面信息
  await loadPageInfo();

  // 绑定事件
  $('saveBtn').addEventListener('click', saveAsset);
  $('openBtn').addEventListener('click', openGeoSystem);
  $('apiBase').addEventListener('change', saveApiConfig);
});

// 加载当前页面信息
async function loadPageInfo() {
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

    $('pageInfo').innerHTML = `
      <div><strong>${tab.title || '未知页面'}</strong></div>
      <div class="url">${tab.url || ''}</div>
    `;
    $('title').value = tab.title || '';

    // 尝试通过content script获取页面正文（用于快速预览）
    try {
      const results = await chrome.scripting.executeScript({
        target: { tabId: tab.id },
        func: getPageContent
      });
      if (results && results[0] && results[0].result) {
        const content = results[0].result;
        if (content.description) {
          $('remark').value = content.description;
        }
      }
    } catch (e) {
      console.log('无法获取页面内容:', e);
    }
  } catch (e) {
    $('pageInfo').innerHTML = '<div style="color:#ff4d4f">无法获取当前页面信息</div>';
  }
}

// 在页面上下文中执行的函数（获取页面描述）
function getPageContent() {
  // 尝试获取meta description
  const metaDesc = document.querySelector('meta[name="description"]');
  const ogDesc = document.querySelector('meta[property="og:description"]');

  return {
    description: (metaDesc?.content || ogDesc?.content || '').substring(0, 200)
  };
}

// 保存API配置
async function saveApiConfig() {
  await chrome.storage.sync.set({ apiBase: $('apiBase').value });
  showStatus('API配置已保存', 'success');
}

// 保存资产
async function saveAsset() {
  const title = $('title').value.trim();
  if (!title) {
    showStatus('请填写标题', 'error');
    return;
  }

  const apiBase = $('apiBase').value.trim();
  if (!apiBase) {
    showStatus('请配置API地址', 'error');
    return;
  }

  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

  showStatus('正在保存...', 'loading');
  $('saveBtn').disabled = true;

  try {
    const response = await fetch(`${apiBase}/asset/sources`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        source_type: 'url',
        title: title,
        url: tab.url,
        source_site: new URL(tab.url).hostname,
        category: $('category').value,
        tags: $('tags').value,
        content: $('remark').value,
      }),
    });

    const result = await response.json();

    if (result.code === 0) {
      showStatus('收藏成功！正在后台解析网页...', 'success');
      $('saveBtn').textContent = '已收藏 ✓';
    } else {
      showStatus(result.message || '保存失败', 'error');
      $('saveBtn').disabled = false;
    }
  } catch (e) {
    showStatus(`网络错误: ${e.message}`, 'error');
    $('saveBtn').disabled = false;
  }
}

// 打开GEO系统
function openGeoSystem() {
  const apiBase = $('apiBase').value.trim();
  // 从API地址提取前端地址
  const match = apiBase.match(/^(https?:\/\/[^\/]+)/);
  if (match) {
    chrome.tabs.create({ url: `${match[1]}/geo/asset` });
  } else {
    chrome.tabs.create({ url: 'http://10.16.190.100:8028/geo/asset' });
  }
}

// 显示状态
function showStatus(msg, type) {
  const el = $('status');
  el.textContent = msg;
  el.className = `status ${type}`;

  if (type === 'success') {
    setTimeout(() => {
      el.className = 'status';
    }, 3000);
  }
}
