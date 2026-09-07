import unittest
import sys
import os

# Ensure UTF-8 output encoding for Windows console
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from app import app, BIOMARKER_CLINICAL_INFO


class TestProfessionalFeatures(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def test_upload_sample_requires_login(self):
        """Test that /upload_sample redirects to login when unauthenticated."""
        response = self.client.get('/upload_sample')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.location)

    def test_upload_sample_authenticated(self):
        """Test that /upload_sample successfully generates a sample report for logged in user."""
        with self.client.session_transaction() as sess:
            sess['user'] = 'test_user_demo'

        response = self.client.get('/upload_sample', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn('Sample Comprehensive Lab Report', html)
        self.assertIn('Hemoglobin', html)
        self.assertIn('Range Meter', html)
        self.assertIn('Export PDF', html)

    def test_custom_404_handler(self):
        """Test custom 404 error page rendering."""
        response = self.client.get('/non_existent_route_12345')
        self.assertEqual(response.status_code, 404)
        html = response.get_data(as_text=True)
        self.assertIn('404', html)
        self.assertIn('Page Not Found', html)

    def test_biomarker_clinical_info_context(self):
        """Test that biomarker guidance dictionary contains all core parameters."""
        required_keys = ["Hemoglobin", "WBC", "RBC", "Platelet", "Sugar", "Cholesterol"]
        for key in required_keys:
            self.assertIn(key, BIOMARKER_CLINICAL_INFO)
            self.assertIn("category", BIOMARKER_CLINICAL_INFO[key])
            self.assertIn("description", BIOMARKER_CLINICAL_INFO[key])
            self.assertIn("tips", BIOMARKER_CLINICAL_INFO[key])

    def test_signup_page_has_password_meter(self):
        """Test that signup template contains password strength elements."""
        response = self.client.get('/signup')
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn('pwd-strength-bar', html)
        self.assertIn('checkPasswordStrength', html)


if __name__ == '__main__':
    unittest.main()
