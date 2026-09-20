// GEO数字资产助手 - Content Script
// 在页面中运行，提供右键快捷收藏等功能

// 监听来自popup或background的消息
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'getPageContent') {
    sendResponse({
      title: document.title,
      url: window.location.href,
      description: getMetaDescription(),
      content: getMainContent(),
    });
  }
  return true;
});

// 获取meta描述
function getMetaDescription() {
  const metaDesc = document.querySelector('meta[name="description"]');
  const ogDesc = document.querySelector('meta[property="og:description"]');
  return (metaDesc?.content || ogDesc?.content || '').substring(0, 500);
}

// 获取主要内容（简化版，用于预览）
function getMainContent() {
  // 尝试找到文章主体
  const article = document.querySelector('article') ||
                  document.querySelector('.article-content') ||
                  document.querySelector('.post-content') ||
                  document.querySelector('#content') ||
                  document.querySelector('main');

  if (article) {
    return article.innerText.substring(0, 1000);
  }
  return document.body.innerText.substring(0, 1000);
}

// 标记GEO已收藏（可选：在页面上显示已收藏标记）
(function addBookmarkIndicator() {
  // 这里可以添加一个小图标，表示该页面已收藏
  // 暂不实现，避免影响用户浏览体验
})();
