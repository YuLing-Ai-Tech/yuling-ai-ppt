// 放映内核 · 启动顺序：拆内容页标题 → 组件启动步骤 → 风格启动步骤（都按注册顺序）→ 缩放舞台 → 显示首页或 #页码
splitHeadingLines();
(window.componentBootSteps || []).forEach(step => step());
(window.styleBootSteps || []).forEach(step => step());
fitStage();
slides[0].classList.add("active");
show((parseInt(location.hash.slice(1), 10) || 1) - 1);
