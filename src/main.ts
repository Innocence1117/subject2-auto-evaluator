const canvas = document.createElement('canvas');
canvas.width = 800;
canvas.height = 600;
//600*800
document.body.appendChild(canvas);

const ctx = canvas.getContext('2d')!;

// 画背景
ctx.fillStyle = '#333333';
ctx.fillRect(0, 0, canvas.width, canvas.height);

// 画线（倒车入库的库位线）
ctx.strokeStyle = '#ffffff';
ctx.lineWidth = 3;
ctx.beginPath();
ctx.moveTo(100, 100);
ctx.lineTo(100, 300);
ctx.lineTo(200, 300);
ctx.lineTo(200, 100);
ctx.stroke();

// 画车（绿色方块占位）
ctx.fillStyle = '#00aa00';
ctx.fillRect(120, 150, 50, 80);