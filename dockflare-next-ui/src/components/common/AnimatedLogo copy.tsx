"use client"; // DockFlare PORTAL LOGO the small containers are our Docker Services :) from an showerthought ..

import React, { useEffect, useRef } from 'react';
import styles from './AnimatedLogo.module.css'; 

const AnimatedLogo: React.FC = () => {
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const logoContainerRef = useRef<HTMLDivElement>(null); 
    const animationFrameId = useRef<number | null>(null);
    const allContainersRef = useRef<any[]>([]); 

    useEffect(() => {
        const canvas = canvasRef.current;
        const logoContainer = logoContainerRef.current;
        if (!canvas || !logoContainer) return;

        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        const resizeCanvas = () => {
            if (logoContainer && canvas) {
                canvas.width = logoContainer.offsetWidth;
                canvas.height = logoContainer.offsetHeight;
            }
        };

        resizeCanvas();
        window.addEventListener('resize', resizeCanvas);

        const BASE_SCALE_FACTOR = 0.5; 
        const CONTAINER_WIDTH = 33 * BASE_SCALE_FACTOR;
        const CONTAINER_HEIGHT = 20 * BASE_SCALE_FACTOR;
        const CONTAINER_SPEED = 0.5; 
        const CONTAINER_COLORS = ['#1a4a7f', '#60A5FA', '#BFDBFE'];
        const PIXEL_SIZE = 4 * BASE_SCALE_FACTOR; 
        const PORTAL_BORDER_WIDTH = 6 * BASE_SCALE_FACTOR;
        const PIXELATION_DISTANCE = 35 * BASE_SCALE_FACTOR;
        const bluePortalElement = logoContainer.querySelector(`.${styles.inPortal}`) as HTMLElement;
        const orangePortalElement = logoContainer.querySelector(`.${styles.outPortal}`) as HTMLElement;

        if (!bluePortalElement || !orangePortalElement) {
            console.error("Portal elements not found. Check CSS module class names.");
            return;
        }
        
        const BLUE_PORTAL_CSS_LEFT = bluePortalElement.offsetLeft;
        const BLUE_PORTAL_WIDTH = bluePortalElement.offsetWidth;
        const BPRP = BLUE_PORTAL_CSS_LEFT + BLUE_PORTAL_WIDTH - PORTAL_BORDER_WIDTH;

        const ORANGE_PORTAL_CSS_LEFT = orangePortalElement.offsetLeft;
        const OPLP = ORANGE_PORTAL_CSS_LEFT + PORTAL_BORDER_WIDTH;
        
        const BLUE_STREAM_TURN_X = BPRP - CONTAINER_WIDTH - PIXELATION_DISTANCE - (18 * BASE_SCALE_FACTOR);
        const ORANGE_STREAM_TURN_X = OPLP + PIXELATION_DISTANCE + (48 * BASE_SCALE_FACTOR);
        
        const CONTAINER_TRAVEL_Y_POSITIONS = [
            logoContainer.offsetHeight / 2 - CONTAINER_HEIGHT / 2 - (35 * BASE_SCALE_FACTOR),
            logoContainer.offsetHeight / 2 - CONTAINER_HEIGHT / 2,     
            logoContainer.offsetHeight / 2 - CONTAINER_HEIGHT / 2 + (35 * BASE_SCALE_FACTOR) 
        ];

        const NUM_CONTAINERS_PER_STREAM = 4;
        const STAGGER_SPAWN_DELAY = 500;

        class Container {
            x: number;
            y: number;
            width: number;
            height: number;
            color: string;
            portalAffinity: 'blue' | 'orange';
            stage: number;
            isPixelated: boolean;
            pixelationIntensity: number;
            isVisible: boolean;
            direction: number;
            turnAroundPointX: number;
            reentryPlaneX: number;

            constructor(portalAffinity: 'blue' | 'orange') {
                this.width = CONTAINER_WIDTH;
                this.height = CONTAINER_HEIGHT;
                this.color = CONTAINER_COLORS[Math.floor(Math.random() * CONTAINER_COLORS.length)];
                this.y = CONTAINER_TRAVEL_Y_POSITIONS[Math.floor(Math.random() * CONTAINER_TRAVEL_Y_POSITIONS.length)];
                
                this.portalAffinity = portalAffinity;
                this.stage = 0;
                this.isPixelated = true;
                this.pixelationIntensity = 1;
                this.isVisible = true;
                
                if (this.portalAffinity === 'blue') {
                    this.x = BPRP - this.width;
                    this.direction = -1;
                    this.turnAroundPointX = BLUE_STREAM_TURN_X;
                    this.reentryPlaneX = BPRP;
                } else {
                    this.x = OPLP;
                    this.direction = 1;
                    this.turnAroundPointX = ORANGE_STREAM_TURN_X;
                    this.reentryPlaneX = OPLP;
                }
            }
            
            reset() {
                this.y = CONTAINER_TRAVEL_Y_POSITIONS[Math.floor(Math.random() * CONTAINER_TRAVEL_Y_POSITIONS.length)];
                this.color = CONTAINER_COLORS[Math.floor(Math.random() * CONTAINER_COLORS.length)];
                this.stage = 0;
                this.isPixelated = true;
                this.pixelationIntensity = 1;
                this.isVisible = true;
                if (this.portalAffinity === 'blue') {
                    this.x = BPRP - this.width;
                    this.direction = -1;
                } else {
                    this.x = OPLP;
                    this.direction = 1;
                }
            }

            updateVisualState() {
                this.isPixelated = false; this.pixelationIntensity = 0;
                let progress = 0;
                const leadingX = this.direction === 1 ? this.x + this.width : this.x;
                const trailingX = this.direction === 1 ? this.x : this.x + this.width;

                if (this.portalAffinity === 'blue') {
                    const emergePlaneFront = BPRP - this.width;
                    if (this.stage === 0) {
                        if (leadingX > emergePlaneFront - PIXELATION_DISTANCE && leadingX <= emergePlaneFront) {
                            this.isPixelated = true;
                            progress = (emergePlaneFront - leadingX) / PIXELATION_DISTANCE;
                            this.pixelationIntensity = 1 - Math.min(1, Math.max(0, progress));
                        } else if (leadingX > emergePlaneFront) { this.isPixelated = true; this.pixelationIntensity = 1; }
                    } else { 
                        if (leadingX > BPRP - PIXELATION_DISTANCE && trailingX < BPRP) {
                            this.isPixelated = true;
                            progress = (leadingX - (BPRP - PIXELATION_DISTANCE)) / PIXELATION_DISTANCE;
                            this.pixelationIntensity = Math.min(1, Math.max(0, progress));
                        } else if (trailingX >= BPRP) { this.isVisible = false; }
                    }
                } else { 
                    if (this.stage === 0) { 
                        if (leadingX < OPLP + PIXELATION_DISTANCE && leadingX >= OPLP) {
                            this.isPixelated = true;
                            progress = (leadingX - OPLP) / PIXELATION_DISTANCE;
                            this.pixelationIntensity = 1 - Math.min(1, Math.max(0, progress));
                        } else if (leadingX < OPLP) { this.isPixelated = true; this.pixelationIntensity = 1; }
                    } else { 
                        if (leadingX < OPLP + PIXELATION_DISTANCE && trailingX > OPLP) {
                            this.isPixelated = true;
                            progress = ((OPLP + PIXELATION_DISTANCE) - leadingX) / PIXELATION_DISTANCE;
                            this.pixelationIntensity = Math.min(1, Math.max(0, progress));
                        } else if (trailingX <= OPLP) { this.isVisible = false; }
                    }
                }
            }

            update() {
                this.x += CONTAINER_SPEED * this.direction;
                this.updateVisualState();

                const leadingX = this.direction === 1 ? this.x + this.width : this.x;
                const trailingX = this.direction === 1 ? this.x : this.x + this.width;

                if (this.stage === 0) {
                    if ((this.direction === -1 && leadingX <= this.turnAroundPointX) ||
                        (this.direction === 1 && leadingX >= this.turnAroundPointX)) {
                        this.direction *= -1;
                        this.stage = 1;
                    }
                } else { 
                    if (!this.isVisible || 
                        (this.portalAffinity === 'blue' && trailingX >= this.reentryPlaneX) ||
                        (this.portalAffinity === 'orange' && trailingX <= this.reentryPlaneX)) {
                        this.reset(); 
                    }
                }
            }

            draw(currentCtx: CanvasRenderingContext2D) {
                if (!this.isVisible) return;
                currentCtx.fillStyle = this.color;
                if (this.isPixelated && this.pixelationIntensity > 0.001) {
                    const numPixelsX = Math.floor(this.width / PIXEL_SIZE);
                    const numPixelsY = Math.floor(this.height / PIXEL_SIZE);
                    for (let i = 0; i < numPixelsX; i++) {
                        for (let j = 0; j < numPixelsY; j++) {
                            if (Math.random() < this.pixelationIntensity) {
                                currentCtx.fillRect( this.x + i * PIXEL_SIZE, this.y + j * PIXEL_SIZE, PIXEL_SIZE, PIXEL_SIZE );
                            }
                        }
                    }
                } else if (!this.isPixelated || this.pixelationIntensity <= 0.001) {
                    currentCtx.fillRect(this.x, this.y, this.width, this.height);
                }
            }
        } 

        allContainersRef.current = []; 
        const timeouts: NodeJS.Timeout[] = [];

        const initializeStreams = () => {
            for (let i = 0; i < NUM_CONTAINERS_PER_STREAM; i++) {
                timeouts.push(setTimeout(() => {
                    allContainersRef.current.push(new Container('blue'));
                }, i * STAGGER_SPAWN_DELAY));

                timeouts.push(setTimeout(() => {
                    allContainersRef.current.push(new Container('orange'));
                }, i * STAGGER_SPAWN_DELAY + STAGGER_SPAWN_DELAY / 2));
            }
        };

        const animate = () => {
            if (!canvasRef.current || !ctx) return; 
            ctx.clearRect(0, 0, canvasRef.current.width, canvasRef.current.height);
            for (let i = 0; i < allContainersRef.current.length; i++) {
                allContainersRef.current[i].update();
                allContainersRef.current[i].draw(ctx);
            }
            animationFrameId.current = requestAnimationFrame(animate);
        };
        
        initializeStreams();
        animate();

        return () => { 
            window.removeEventListener('resize', resizeCanvas);
            if (animationFrameId.current) {
                cancelAnimationFrame(animationFrameId.current);
            }
            timeouts.forEach(clearTimeout); 
            allContainersRef.current = []; 
        };
    }, []); 

    return (
        <div ref={logoContainerRef} className={styles.logoContainer}>
            <canvas ref={canvasRef} className={styles.canvasElement}></canvas>
            <span className={`${styles.logoText} ${styles.dockText}`}>Dock</span>
            <span className={`${styles.logoText} ${styles.flareText}`}>Flare</span>
            <div className={`${styles.portal} ${styles.inPortal}`}></div>
            <div className={`${styles.portal} ${styles.outPortal}`}></div>
        </div>
    );
};

export default AnimatedLogo;