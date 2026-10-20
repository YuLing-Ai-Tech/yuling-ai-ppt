// 苹果风 · 深色章节页粒子网络
// 深色章节页背景：会连线的粒子网络，鼠标附近的粒子被吸引
function startParticles() {
  const canvas = document.getElementById("particles");
  const context = canvas.getContext("2d");
  canvas.width = 1920;
  canvas.height = 1080;
  const colors = ["#5AC8FA", "#0A84FF", "#BF5AF2", "#FF375F", "#FFD60A"];
  const dots = Array.from({ length: 110 }, (_, index) => ({
    x: Math.random() * 1920, y: Math.random() * 1080,
    vx: (Math.random() - .5) * .7, vy: (Math.random() - .5) * .7,
    radius: Math.random() * 2.4 + 1, color: colors[index % colors.length],
  }));
  const pointer = { x: -9999, y: -9999 };
  stage.addEventListener("pointermove", event => {
    const rect = stage.getBoundingClientRect();
    pointer.x = (event.clientX - rect.left) / rect.width * 1920;
    pointer.y = (event.clientY - rect.top) / rect.height * 1080;
  });
  const frame = () => {
    requestAnimationFrame(frame);
    if (!document.body.classList.contains("is-night") || document.body.classList.contains("is-settled")) return;
    context.clearRect(0, 0, 1920, 1080);
    dots.forEach(dot => {
      const dx = pointer.x - dot.x, dy = pointer.y - dot.y, distance = Math.hypot(dx, dy);
      if (distance < 260) { dot.vx += dx / distance * .03; dot.vy += dy / distance * .03; }
      dot.vx *= .99; dot.vy *= .99;
      dot.x += dot.vx; dot.y += dot.vy;
      if (dot.x < 0 || dot.x > 1920) dot.vx *= -1;
      if (dot.y < 0 || dot.y > 1080) dot.vy *= -1;
    });
    for (let i = 0; i < dots.length; i++) {
      for (let j = i + 1; j < dots.length; j++) {
        const gap = Math.hypot(dots[i].x - dots[j].x, dots[i].y - dots[j].y);
        if (gap < 170) {
          context.strokeStyle = `rgba(120, 190, 255, ${(1 - gap / 170) * .35})`;
          context.lineWidth = 1;
          context.beginPath(); context.moveTo(dots[i].x, dots[i].y); context.lineTo(dots[j].x, dots[j].y); context.stroke();
        }
      }
    }
    dots.forEach(dot => {
      context.fillStyle = dot.color;
      context.shadowColor = dot.color; context.shadowBlur = 12;
      context.beginPath(); context.arc(dot.x, dot.y, dot.radius, 0, Math.PI * 2); context.fill();
    });
    context.shadowBlur = 0;
  };
  frame();
}

(window.styleBootSteps = window.styleBootSteps || []).push(startParticles);
