"""Design & UI/UX Agent — generates designs, wireframes, and prototypes."""

from agents.base_agent import BaseAgent

SYSTEM_PROMPT = """You are the Design Agent, an expert in UI/UX design.

You generate complete designs including:

1. Wireframes:
   - Low-fidelity sketches
   - High-fidelity mockups
   - Interactive prototypes

2. Design Systems:
   - Color palettes
   - Typography
   - Spacing and grids
   - Component libraries
   - Interaction patterns

3. User Flows:
   - User journey maps
   - Flow diagrams
   - Task flows

4. Animations:
   - CSS animations
   - Micro-interactions
   - Page transitions
   - Loading animations

5. Responsive Designs:
   - Mobile-first
   - Tablet layouts
   - Desktop layouts

6. Accessibility:
   - WCAG 2.1 AA compliance
   - Color contrast
   - Screen reader support

Your designs must be user-centered, consistent, accessible, and
production-ready. Provide code for the designs (HTML/CSS/JS, React, Figma)."""

DEFAULT_PALETTE = {
    "primary": "#2563EB",
    "secondary": "#7C3AED",
    "success": "#10B981",
    "danger": "#EF4444",
    "warning": "#F59E0B",
    "info": "#3B82F6",
    "dark": "#1F2937",
    "light": "#F9FAFB",
}


class DesignAgent(BaseAgent):
    def __init__(self, **kwargs):
        super().__init__(
            name="Design",
            description="UI/UX design, wireframes, prototypes, and design systems",
            system_prompt=SYSTEM_PROMPT,
            **kwargs,
        )

    def design_system(self, primary: str = None) -> dict:
        """Generate a deterministic design token set."""
        colors = dict(DEFAULT_PALETTE)
        if primary:
            colors["primary"] = primary
        return {
            "colors": colors,
            "typography": {
                "font_family": "Inter, system-ui, sans-serif",
                "heading_sizes": {"h1": "2.5rem", "h2": "2rem", "h3": "1.75rem",
                                  "h4": "1.5rem", "h5": "1.25rem", "h6": "1rem"},
                "body_sizes": {"large": "1.125rem", "default": "1rem", "small": "0.875rem"},
            },
            "spacing": {"xs": "0.25rem", "sm": "0.5rem", "md": "1rem", "lg": "1.5rem",
                        "xl": "2rem", "2xl": "3rem", "3xl": "4rem"},
            "components": {
                "buttons": "rounded-md, primary fill, hover:opacity-90",
                "inputs": "rounded-md border, focus ring",
                "cards": "rounded-lg shadow, 8px padding",
            },
        }
