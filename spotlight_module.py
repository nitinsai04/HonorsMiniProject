"""
Spotlight Module for Gesture-Controlled Presentations
"""

import cv2
import numpy as np
import subprocess
import platform


class SpotlightController:
    def __init__(self, radius=150, dim_opacity=0.7, hardware_dim_enabled=True, dimmed_brightness=0.3):
        self.radius = radius
        self.dim_opacity = dim_opacity
        self.hardware_dim_enabled = hardware_dim_enabled
        self.dimmed_brightness = dimmed_brightness
        self.is_active = False
        self.is_mac = platform.system() == 'Darwin'
        self.normal_brightness = 1.0
        
        if self.is_mac and self.hardware_dim_enabled:
            self.normal_brightness = self._get_brightness()
            self._check_brightness_available()
    
    def _check_brightness_available(self):
        try:
            subprocess.run(['brightness', '-l'], capture_output=True, check=True, timeout=1)
            print("✓ Hardware brightness control available")
            print(f"  Current brightness: {self.normal_brightness:.2f}")
        except:
            print("✗ Hardware brightness not available (Install: brew install brightness)")
            self.hardware_dim_enabled = False
    
    def _set_brightness(self, level):
        if not self.is_mac or not self.hardware_dim_enabled:
            return False
        try:
            subprocess.run(['brightness', str(level)], capture_output=True, check=True, timeout=2)
            return True
        except:
            return False
    
    def _get_brightness(self):
        if not self.is_mac:
            return 1.0
        try:
            result = subprocess.run(['brightness', '-l'], capture_output=True, text=True, check=True, timeout=2)
            if 'brightness' in result.stdout:
                return float(result.stdout.split('brightness')[1].strip())
        except:
            pass
        return 1.0
    
    def create_overlay(self, img, center_x, center_y):
        if not self.is_active:
            return img
        
        result = img.copy()
        dark_overlay = np.zeros_like(img)
        mask = np.zeros((img.shape[0], img.shape[1]), dtype=np.uint8)
        cv2.circle(mask, (center_x, center_y), self.radius, 255, -1)
        mask = cv2.GaussianBlur(mask, (51, 51), 0)
        mask_float = mask.astype(float) / 255
        mask_3channel = np.stack([mask_float] * 3, axis=-1)
        
        result = (result * mask_3channel + 
                 dark_overlay * (1 - mask_3channel) * self.dim_opacity + 
                 result * (1 - mask_3channel) * (1 - self.dim_opacity))
        
        cv2.circle(result, (center_x, center_y), 5, (0, 255, 255), -1)
        return result.astype(np.uint8)
    
    def toggle(self):
        self.is_active = not self.is_active
        if self.is_active:
            print("🔦 Spotlight: ON")
            if self.is_mac and self.hardware_dim_enabled:
                self.normal_brightness = self._get_brightness()
                self._set_brightness(self.dimmed_brightness)
        else:
            print("💡 Spotlight: OFF")
            if self.is_mac and self.hardware_dim_enabled:
                self._set_brightness(self.normal_brightness)
        return self.is_active
    
    def increase_radius(self, amount=20):
        self.radius = min(self.radius + amount, 400)
        print(f"Spotlight radius: {self.radius}")
        return self.radius
    
    def decrease_radius(self, amount=20):
        self.radius = max(self.radius - amount, 50)
        print(f"Spotlight radius: {self.radius}")
        return self.radius
    
    def increase_dim(self, amount=0.1):
        self.dim_opacity = min(self.dim_opacity + amount, 0.95)
        print(f"Dim opacity: {self.dim_opacity:.1f}")
        return self.dim_opacity
    
    def decrease_dim(self, amount=0.1):
        self.dim_opacity = max(self.dim_opacity - amount, 0.3)
        print(f"Dim opacity: {self.dim_opacity:.1f}")
        return self.dim_opacity
    
    def toggle_hardware_control(self):
        self.hardware_dim_enabled = not self.hardware_dim_enabled
        print(f"Hardware brightness: {'ENABLED' if self.hardware_dim_enabled else 'DISABLED'}")
        if not self.hardware_dim_enabled and self.is_active and self.is_mac:
            self._set_brightness(self.normal_brightness)
        return self.hardware_dim_enabled
    
    def cleanup(self):
        if self.is_active and self.is_mac and self.hardware_dim_enabled:
            self._set_brightness(self.normal_brightness)
            print("Brightness restored")