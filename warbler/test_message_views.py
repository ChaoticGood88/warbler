"""Message View tests."""

# Run these tests like:
#
#    FLASK_ENV=production python -m unittest test_message_views.py

import os
from unittest import TestCase

from models import db, connect_db, Message, User

os.environ['DATABASE_URL'] = "postgresql:///warbler-test"

from app import app, CURR_USER_KEY

db.create_all()

# Don't have WTForms use CSRF at all, since it's a pain to test
app.config['WTF_CSRF_ENABLED'] = False


class MessageViewTestCase(TestCase):
    """Test views for messages."""

    def setUp(self):
        """Create test client, add sample data."""

        User.query.delete()
        Message.query.delete()

        self.client = app.test_client()

        self.testuser = User.signup(username="testuser",
                                    email="test@test.com",
                                    password="testuser",
                                    image_url=None)

        self.other_user = User.signup(username="otheruser",
                                      email="other@test.com",
                                      password="password",
                                      image_url=None)

        db.session.commit()

        self.message = Message(
            text="Test message",
            user_id=self.testuser.id
        )
        db.session.add(self.message)
        db.session.commit()

    def tearDown(self):
        """Rollback session after each test."""
        db.session.rollback()

    def test_add_message(self):
        """Can a logged-in user add a message?"""

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id

            resp = c.post("/messages/new", data={"text": "Hello"})

            # Make sure it redirects
            self.assertEqual(resp.status_code, 302)

            msg = Message.query.filter_by(text="Hello").one()
            self.assertEqual(msg.text, "Hello")
            self.assertEqual(msg.user_id, self.testuser.id)

    def test_add_message_logged_out(self):
        """Is adding a message forbidden for logged-out users?"""

        with self.client as c:
            resp = c.post("/messages/new", data={"text": "Hello"}, follow_redirects=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("Access unauthorized", str(resp.data))

    def test_show_message(self):
        """Can a user view a specific message?"""

        with self.client as c:
            resp = c.get(f"/messages/{self.message.id}")

            self.assertEqual(resp.status_code, 200)
            self.assertIn("Test message", str(resp.data))

    def test_delete_message(self):
        """Can a logged-in user delete their message?"""

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id

            resp = c.post(f"/messages/{self.message.id}/delete", follow_redirects=True)
            self.assertEqual(resp.status_code, 200)

            msg = Message.query.get(self.message.id)
            self.assertIsNone(msg)

    def test_delete_message_logged_out(self):
        """Is deleting a message forbidden for logged-out users?"""

        with self.client as c:
            resp = c.post(f"/messages/{self.message.id}/delete", follow_redirects=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("Access unauthorized", str(resp.data))

    def test_delete_other_users_message(self):
        """Is deleting another user's message forbidden?"""

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.other_user.id

            resp = c.post(f"/messages/{self.message.id}/delete", follow_redirects=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("Access unauthorized", str(resp.data))

            msg = Message.query.get(self.message.id)
            self.assertIsNotNone(msg)
