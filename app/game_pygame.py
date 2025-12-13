"""Pygame-based Halftime Game interface.

This provides a native desktop app with proper keyboard support.
All plots must be pre-generated using scripts/generate_cache.py.

Usage:
    python -m app.game_pygame
"""
import pygame
import sys
from pathlib import Path
import pickle
from PIL import Image
import time
from typing import Dict, Optional, Tuple

# Constants
CACHE_DIR = Path("cache/plots")
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 900
FLASH_DURATION_MS = 100  # 100ms flash


class HalftimeGame:
    """Main game class for Pygame interface."""
    
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Halftime Game 🏀")
        
        # Game state
        self.game_ids = self._get_all_cached_games()
        self.residual_data = self._load_all_residual_data(self.game_ids)
        self.cached_images = self._preload_images()
        
        self.current_game_index = 0
        self.score_tally = {'correct': 0, 'total': 0}
        self.game_states: Dict[str, dict] = {}
        
        # Flash state
        self.flash_active = False
        self.flash_color = None
        self.flash_start_time = 0
        
        # Fonts
        self.font_large = pygame.font.Font(None, 48)
        self.font_medium = pygame.font.Font(None, 36)
        self.font_small = pygame.font.Font(None, 24)
        
        if not self.game_ids:
            print("ERROR: No cached plots found. Please run `python scripts/generate_cache.py` first.")
            sys.exit(1)
    
    def _get_all_cached_games(self) -> list:
        """Get all game IDs from cache."""
        if not CACHE_DIR.exists():
            return []
        
        game_ids = set()
        for png_file in CACHE_DIR.glob("*.png"):
            if png_file.name.endswith('_residuals.png'):
                continue
            game_id = png_file.stem
            game_ids.add(game_id)
        
        return sorted(list(game_ids))
    
    def _load_all_residual_data(self, game_ids: list) -> dict:
        """Load all residual data files."""
        residuals = {}
        for game_id in game_ids:
            pkl_path = CACHE_DIR / f"{game_id}_residuals.pkl"
            if pkl_path.exists():
                try:
                    with open(pkl_path, 'rb') as f:
                        residuals[game_id] = pickle.load(f)
                except Exception as e:
                    print(f"Error loading residual data for {game_id}: {e}")
        return residuals
    
    def _preload_images(self) -> dict:
        """Preload all plot images into memory."""
        images = {}
        for game_id in self.game_ids:
            plot_path = CACHE_DIR / f"{game_id}.png"
            if plot_path.exists():
                try:
                    # Load image directly with pygame (faster)
                    try:
                        img_surface = pygame.image.load(str(plot_path))
                        images[game_id] = img_surface
                    except pygame.error:
                        # Fallback: use PIL if pygame can't load it
                        pil_img = Image.open(plot_path)
                        if pil_img.mode != 'RGB':
                            pil_img = pil_img.convert('RGB')
                        # Convert PIL to pygame via numpy
                        import numpy as np
                        img_array = np.array(pil_img)
                        img_surface = pygame.surfarray.make_surface(img_array.swapaxes(0, 1))
                        images[game_id] = img_surface
                except Exception as e:
                    print(f"Error loading image for {game_id}: {e}")
        return images
    
    def _get_game_state(self, game_id: str) -> dict:
        """Get or create game state."""
        if game_id not in self.game_states:
            self.game_states[game_id] = {
                'prediction_made': False,
                'user_prediction': None,
                'correctness': None
            }
        return self.game_states[game_id]
    
    def _calculate_correctness(self, user_prediction: str, residual_data: dict) -> Tuple[bool, str]:
        """Calculate if user prediction was correct.
        
        Uses p_value_p2 to determine fast/slow:
        - p_value_p2 > 0.5 means Period 2 was SLOWER than expected
        - p_value_p2 < 0.5 means Period 2 was FASTER than expected
        """
        p_value_p2 = residual_data.get('p_value_p2', 0.5)
        actual_result = "slow" if p_value_p2 > 0.5 else "fast"
        is_correct = (user_prediction == actual_result)
        return is_correct, actual_result
    
    def _handle_prediction(self, prediction: str):
        """Handle user prediction (fast or slow)."""
        if self.current_game_index >= len(self.game_ids):
            return
        
        current_game_id = self.game_ids[self.current_game_index]
        game_state = self._get_game_state(current_game_id)
        residual_data = self.residual_data.get(current_game_id)
        
        if game_state['prediction_made']:
            return  # Already made prediction
        
        game_state['user_prediction'] = prediction
        game_state['prediction_made'] = True
        
        if residual_data and residual_data.get('p_value_p2') is not None:
            # Calculate correctness
            is_correct, actual_result = self._calculate_correctness(prediction, residual_data)
            game_state['correctness'] = is_correct
            
            # Update score
            self.score_tally['total'] += 1
            if is_correct:
                self.score_tally['correct'] += 1
            
            # Flash screen with color based on P2 result
            p_value_p2 = residual_data.get('p_value_p2', 0.5)
            flash_color = (0, 200, 0) if p_value_p2 < 0.5 else (200, 0, 0)  # Green for faster, red for slower
            self.flash_active = True
            self.flash_color = flash_color
            self.flash_start_time = pygame.time.get_ticks()
            
            # Set timestamp for showing result text (100ms delay)
            game_state['result_show_time'] = pygame.time.get_ticks() + 100
            
            # Auto-advance after showing result
            pygame.time.set_timer(pygame.USEREVENT, 1500)  # Advance after 1.5 seconds
    
    def _advance_to_next_game(self):
        """Move to next game."""
        if self.current_game_index < len(self.game_ids) - 1:
            self.current_game_index += 1
        else:
            # Loop back to start
            self.current_game_index = 0
            # Reset game states for replay
            self.game_states = {}
            self.score_tally = {'correct': 0, 'total': 0}
    
    def _draw(self):
        """Draw everything to screen."""
        self.screen.fill((255, 255, 255))  # White background
        
        if self.current_game_index >= len(self.game_ids):
            return
        
        current_game_id = self.game_ids[self.current_game_index]
        game_state = self._get_game_state(current_game_id)
        residual_data = self.residual_data.get(current_game_id)
        
        # Draw title
        title = self.font_large.render("Halftime Game 🏀", True, (0, 0, 0))
        self.screen.blit(title, (20, 20))
        
        # Draw score
        score = self.score_tally
        if score['total'] > 0:
            percentage = (score['correct'] / score['total']) * 100
            score_text = f"Score: {score['correct']}/{score['total']} ({percentage:.1f}%)"
        else:
            score_text = "Score: 0/0"
        score_surface = self.font_medium.render(score_text, True, (0, 0, 0))
        self.screen.blit(score_surface, (20, 80))
        
        # Draw progress
        progress_text = f"Game {self.current_game_index + 1} of {len(self.game_ids)}"
        progress_surface = self.font_small.render(progress_text, True, (100, 100, 100))
        self.screen.blit(progress_surface, (20, 120))
        
        # Draw plot image
        img = self.cached_images.get(current_game_id)
        if img:
            # Scale image to fit screen (maintain aspect ratio)
            img_width, img_height = img.get_size()
            scale = min((WINDOW_WIDTH - 40) / img_width, (WINDOW_HEIGHT - 200) / img_height)
            new_width = int(img_width * scale)
            new_height = int(img_height * scale)
            scaled_img = pygame.transform.scale(img, (new_width, new_height))
            
            # Center image
            x_offset = (WINDOW_WIDTH - new_width) // 2
            y_offset = 160
            self.screen.blit(scaled_img, (x_offset, y_offset))
        else:
            error_text = self.font_medium.render(f"Plot not found for game {current_game_id}", True, (200, 0, 0))
            self.screen.blit(error_text, (20, 200))
        
        # Draw prediction buttons or result
        if not game_state['prediction_made']:
            # Draw buttons
            button_y = WINDOW_HEIGHT - 100
            button_width = 200
            button_height = 60
            
            # Slow button (left)
            slow_rect = pygame.Rect(WINDOW_WIDTH // 2 - 220, button_y, button_width, button_height)
            pygame.draw.rect(self.screen, (200, 100, 100), slow_rect)
            pygame.draw.rect(self.screen, (0, 0, 0), slow_rect, 3)
            slow_text = self.font_medium.render("🐌 Slow (←)", True, (255, 255, 255))
            text_rect = slow_text.get_rect(center=slow_rect.center)
            self.screen.blit(slow_text, text_rect)
            
            # Fast button (right)
            fast_rect = pygame.Rect(WINDOW_WIDTH // 2 + 20, button_y, button_width, button_height)
            pygame.draw.rect(self.screen, (100, 200, 100), fast_rect)
            pygame.draw.rect(self.screen, (0, 0, 0), fast_rect, 3)
            fast_text = self.font_medium.render("⚡ Fast (→)", True, (255, 255, 255))
            text_rect = fast_text.get_rect(center=fast_rect.center)
            self.screen.blit(fast_text, text_rect)
            
            # Instructions
            inst_text = self.font_small.render("Press ← for Slow, → for Fast", True, (100, 100, 100))
            self.screen.blit(inst_text, (WINDOW_WIDTH // 2 - 150, button_y - 30))
        else:
            # Show result (only after 100ms delay)
            if game_state['correctness'] is not None and residual_data:
                result_show_time = game_state.get('result_show_time', 0)
                current_time = pygame.time.get_ticks()
                
                if current_time >= result_show_time:
                    p_value_p2 = residual_data.get('p_value_p2', 0.5)
                    actual_result = "slower" if p_value_p2 > 0.5 else "faster"
                    
                    if game_state['correctness']:
                        result_text = f"✅ Correct! 2H went {actual_result}"
                        color = (0, 150, 0)
                    else:
                        result_text = f"❌ Incorrect. 2H went {actual_result}"
                        color = (200, 0, 0)
                    
                    result_surface = self.font_medium.render(result_text, True, color)
                    text_rect = result_surface.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT - 50))
                    self.screen.blit(result_surface, text_rect)
        
        # Draw flash overlay if active
        if self.flash_active:
            elapsed = pygame.time.get_ticks() - self.flash_start_time
            if elapsed < FLASH_DURATION_MS:
                # Create semi-transparent overlay
                flash_surface = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
                flash_surface.set_alpha(38)  # ~15% opacity (38/255)
                flash_surface.fill(self.flash_color)
                self.screen.blit(flash_surface, (0, 0))
            else:
                self.flash_active = False
    
    def run(self):
        """Main game loop."""
        clock = pygame.time.Clock()
        running = True
        
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_LEFT:
                        self._handle_prediction("slow")
                    elif event.key == pygame.K_RIGHT:
                        self._handle_prediction("fast")
                    elif event.key == pygame.K_ESCAPE:
                        running = False
                
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:  # Left click
                        mouse_pos = pygame.mouse.get_pos()
                        button_y = WINDOW_HEIGHT - 100
                        
                        # Check if clicked on Slow button
                        if WINDOW_WIDTH // 2 - 220 <= mouse_pos[0] <= WINDOW_WIDTH // 2 - 20:
                            if button_y <= mouse_pos[1] <= button_y + 60:
                                self._handle_prediction("slow")
                        
                        # Check if clicked on Fast button
                        elif WINDOW_WIDTH // 2 + 20 <= mouse_pos[0] <= WINDOW_WIDTH // 2 + 220:
                            if button_y <= mouse_pos[1] <= button_y + 60:
                                self._handle_prediction("fast")
                
                elif event.type == pygame.USEREVENT:
                    # Auto-advance to next game
                    self._advance_to_next_game()
                    pygame.time.set_timer(pygame.USEREVENT, 0)  # Cancel timer
            
            self._draw()
            pygame.display.flip()
            clock.tick(60)  # 60 FPS
        
        pygame.quit()
        sys.exit()


def main():
    """Entry point."""
    game = HalftimeGame()
    game.run()


if __name__ == "__main__":
    main()

