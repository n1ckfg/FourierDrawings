
let canvas = null; 
let context = null;
let time = 0;
const Point = class {
    constructor(x, y) {
        this.x = x;
        this.y = y;
    }
    equals(point) {
        return this.x === point.x && this.y === point.y;
    }
    toString() {
        return '(' + this.x + ', ' + this.y + ')';
    }

};

const FourierCircle = class {
    constructor(speed, radius, initial_angle)
    {
        this.radius = radius;
        this.speed = speed/20;
        this.initial_angle = initial_angle
    }
    // Adds this vector to the current path; the caller strokes all vectors at once.
    draw(ctx, at) 
    {
        var x = at.x + this.radius * Math.cos(this.initial_angle + 2 * Math.PI * time * this.speed);
        var y = at.y + this.radius * Math.sin(this.initial_angle + 2 * Math.PI * time * this.speed);
        ctx.moveTo(at.x, at.y);
        ctx.lineTo(x, y);
    }

    nextCenter(at) 
    {
        var x = at.x + this.radius * Math.cos(this.initial_angle + 2 * Math.PI * time * this.speed);
        var y = at.y + this.radius * Math.sin(this.initial_angle + 2 * Math.PI * time * this.speed);
        return new Point(x, y)
    }
};

// Each path has 2 * count - 1 coefficients: c_0, c_1, c_-1, ..., c_(count-1), c_-(count-1).
let circles_per_path;
let circles;
let animation_id = 0;
let origin = new Point(0, 0);
let wave = [];
let nr_of_paths;
function init_fourier(canvas_elm, constants, count) {
    canvas = canvas_elm;
    context = canvas.getContext('2d');

    if(animation_id !== 0)
        window.cancelAnimationFrame(animation_id);
    circles_per_path = 2 * count - 1;
    time = 0;

    circles = [];
    nr_of_paths = constants.length / circles_per_path;
    wave = [];
    for(let i=0;i<nr_of_paths;i++){
        wave.push([]);
    } 

    for (let i = 0; i < constants.length; i++) {
        let constant = constants[i];
        circles[i] = new FourierCircle(constant.s, constant.r, constant.a);
    }
    animation_id = window.requestAnimationFrame(draw);
}

function draw_wave(ctx,wave,j) {
    for (let i = 1; i < wave[j].length; i++) {
        ctx.beginPath();
        ctx.moveTo(wave[j][i-1].x, wave[j][i-1].y);
        ctx.lineTo(wave[j][i].x, wave[j][i].y);

        let alpha = 1 - i*1.0/wave[j].length;
        
        ctx.strokeStyle = 'rgba(0, 0, 0, ' + alpha + ')';
        ctx.lineWidth = 1;
        ctx.stroke();
    }
} 

function draw() {
    context.clearRect(0,0, canvas.width, canvas.height);

    for(let j=0;j<nr_of_paths;j++){
        let first = j * circles_per_path;
        // c_0 doesn't rotate: it is the fixed start of this path's chain of vectors.
        let new_center = circles[first].nextCenter(origin);
        context.beginPath();
        for(let i = 1; i < circles_per_path; i++) {
            circles[first + i].draw(context, new_center);
            new_center = circles[first + i].nextCenter(new_center);
        }
        context.strokeStyle = 'rgba(202, 126, 86, 0.7)';
        context.lineWidth = 1;
        context.stroke();

        draw_wave(context,wave,j);
        wave[j].unshift(new_center);

        if(wave[j].length > 500) {
            wave[j].pop();
        }
    }

    animation_id = window.requestAnimationFrame(draw);

    time += 0.04;
}
