// src/components/effects/MiniContainer.ts - PORTAL! hours of tweaking....... but fun 

export const MINI_PORTAL_CONFIG = {
  REF_PORTAL_WIDTH: 50, 
  REF_PORTAL_HEIGHT: 70, 
  REF_CONTAINER_BASE_WIDTH_FACTOR: 0.45, 
  REF_CONTAINER_BASE_HEIGHT_FACTOR: 0.18, 
  CONTAINER_SPEED: 0.6, 
  PIXEL_SIZE: 1, 
  PIXELATION_DISTANCE_FACTOR: 0.8, 
  NUM_CONTAINERS_PER_EFFECT: 3,
  STAGGER_SPAWN_DELAY: 800,
  TURN_AROUND_OFFSET_FACTOR_X: 0.4, 
};

export type PortalAffinity = 'blue' | 'orange';

export class MiniContainer {
  x!: number;
  y!: number;
  width!: number;
  height!: number;
  color!: string;
  portalAffinity: PortalAffinity;
  stage!: number;
  isPixelated!: boolean;
  pixelationIntensity!: number;
  isVisible!: boolean;
  direction!: number;
  turnAroundPointX!: number;
  
  canvasHeight: number; 
  canvasWidth: number; 
  colors: string[];
  portalCenterX: number;
  portalRadiusX: number; 
  portalRadiusY: number; 

  constructor(
    portalAffinity: PortalAffinity,
    canvasWidth: number, canvasHeight: number,
    portalCenterX: number, 
    portalRadiusX: number, portalRadiusY: number,
    colors: string[]
  ) {
    this.canvasWidth = canvasWidth;
    this.canvasHeight = canvasHeight;
    this.portalAffinity = portalAffinity;
    this.colors = colors;
    this.portalCenterX = portalCenterX;
    this.portalRadiusX = portalRadiusX;
    this.portalRadiusY = portalRadiusY;

    this.initializeProperties();
  }

  private initializeProperties() {
    this.width = Math.max(MINI_PORTAL_CONFIG.PIXEL_SIZE * 3, 
        MINI_PORTAL_CONFIG.REF_PORTAL_WIDTH * MINI_PORTAL_CONFIG.REF_CONTAINER_BASE_WIDTH_FACTOR * (this.portalRadiusX / (MINI_PORTAL_CONFIG.REF_PORTAL_WIDTH / 2))
    );
    this.height = Math.max(MINI_PORTAL_CONFIG.PIXEL_SIZE * 2, 
        MINI_PORTAL_CONFIG.REF_PORTAL_HEIGHT * MINI_PORTAL_CONFIG.REF_CONTAINER_BASE_HEIGHT_FACTOR * (this.portalRadiusY / (MINI_PORTAL_CONFIG.REF_PORTAL_HEIGHT / 2))
    );
    
    this.color = this.colors[Math.floor(Math.random() * this.colors.length)];
    this.y = (this.canvasHeight / 2) - (this.height / 2) + (Math.random() - 0.5) * (this.portalRadiusY * 0.6);

    this.stage = 0;
    this.isPixelated = true;
    this.pixelationIntensity = 1;
    this.isVisible = true;
    
    const turnOffset = this.portalRadiusX * MINI_PORTAL_CONFIG.TURN_AROUND_OFFSET_FACTOR_X;

    if (this.portalAffinity === 'blue') { 
      this.direction = -1; 
      this.x = this.portalCenterX + this.portalRadiusX * 0.35 - (this.width / 2); 
      this.turnAroundPointX = this.portalCenterX - this.portalRadiusX * 0.5 - turnOffset - this.width; 
    } else { 
      this.direction = 1; 
      this.x = this.portalCenterX - this.portalRadiusX * 0.35 - (this.width / 2); 
      this.turnAroundPointX = this.portalCenterX + this.portalRadiusX * 0.5 + turnOffset; 
    }
    this.updateVisualState();
  }
  
  reset() {
    this.initializeProperties();
  }

  updateVisualState() {
    const pixelationDist = this.portalRadiusX * MINI_PORTAL_CONFIG.PIXELATION_DISTANCE_FACTOR; 
    const visualPortalEdgeInnerLeft = this.portalCenterX - this.portalRadiusX * 0.4; 
    const visualPortalEdgeInnerRight = this.portalCenterX + this.portalRadiusX * 0.4;

    let progress = 0;
    this.isPixelated = false; 
    this.pixelationIntensity = 0;

    const leadingX = this.direction === 1 ? this.x + this.width : this.x;
    const trailingX = this.direction === 1 ? this.x : this.x + this.width;

    if (this.stage === 0) { 
      if (this.direction === -1) { 
        if (leadingX > visualPortalEdgeInnerRight) { 
          this.isPixelated = true; this.pixelationIntensity = 1;
        } else if (leadingX > visualPortalEdgeInnerRight - pixelationDist) { 
          this.isPixelated = true;
          progress = ( (leadingX) - (visualPortalEdgeInnerRight - pixelationDist) ) / pixelationDist;
          this.pixelationIntensity = Math.max(0, 1 - progress);
        }
      } else { 
        if (trailingX < visualPortalEdgeInnerLeft) { 
          this.isPixelated = true; this.pixelationIntensity = 1;
        } else if (trailingX < visualPortalEdgeInnerLeft + pixelationDist) { 
          this.isPixelated = true;
          progress = ( (visualPortalEdgeInnerLeft + pixelationDist) - trailingX ) / pixelationDist;
          this.pixelationIntensity = Math.max(0, 1 - progress);
        }
      }
    } 
    else { 
      if (this.direction === -1) { 
        if (trailingX < visualPortalEdgeInnerLeft + pixelationDist) { 
          this.isPixelated = true;
          progress = ( (visualPortalEdgeInnerLeft + pixelationDist) - trailingX ) / pixelationDist;
          this.pixelationIntensity = Math.min(1, Math.max(0, progress));
        }
        if (trailingX < visualPortalEdgeInnerLeft - this.width) { 
            this.isVisible = false; 
        }
      } else { 
         if (leadingX > visualPortalEdgeInnerRight - pixelationDist) { 
          this.isPixelated = true;
          progress = ( leadingX - (visualPortalEdgeInnerRight - pixelationDist) ) / pixelationDist;
          this.pixelationIntensity = Math.min(1, Math.max(0, progress));
        }
         if (leadingX > visualPortalEdgeInnerRight + this.width) { 
            this.isVisible = false; 
        }
      }
    }
    if (this.pixelationIntensity < 0.05) this.isPixelated = false;
  }

  update() {
    if(!this.isVisible) return; 
    this.x += MINI_PORTAL_CONFIG.CONTAINER_SPEED * this.direction;
    this.updateVisualState(); 
    if (!this.isVisible) { 
        setTimeout(() => this.reset(), 50 + Math.random() * 50); 
        return; 
    }
    if (this.stage === 0) {
        const currentXCenter = this.x + this.width / 2;
        if ((this.direction === -1 && currentXCenter <= this.turnAroundPointX) ||
            (this.direction === 1 && currentXCenter >= this.turnAroundPointX)) {
            this.direction *= -1; 
            this.stage = 1;       
        }
    }
  }

  draw(currentCtx: CanvasRenderingContext2D) {
    if (!this.isVisible || !currentCtx) return; 
    currentCtx.fillStyle = this.color;
    const pixelSize = MINI_PORTAL_CONFIG.PIXEL_SIZE;
    if (this.isPixelated && this.pixelationIntensity > 0.05) { 
        const numPixelsX = Math.max(1, Math.floor(this.width / pixelSize));
        const numPixelsY = Math.max(1, Math.floor(this.height / pixelSize));
        currentCtx.globalAlpha = Math.max(0.1, 1 - this.pixelationIntensity * 0.7); 
        for (let i = 0; i < numPixelsX; i++) {
            for (let j = 0; j < numPixelsY; j++) {
                if (Math.random() > this.pixelationIntensity) { 
                    currentCtx.fillRect( this.x + i * pixelSize, this.y + j * pixelSize, pixelSize, pixelSize );
                }
            }
        }
        currentCtx.globalAlpha = 1.0; 
    } else if (!this.isPixelated) { 
        currentCtx.fillRect(this.x, this.y, this.width, this.height);
    }
  }
}