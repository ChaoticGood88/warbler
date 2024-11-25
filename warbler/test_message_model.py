"""Message model tests."""

# Run these tests like:
#
#    python -m unittest test_message_model.py

import os
from unittest import TestCase
from datetime import datetime
from sqlalchemy.exc import IntegrityError

from app import app
from models import db, User, Message

# Set an environmental variable to use a different test database
os.environ['DATABASE_URL'] = "postgresql:///warbler-test"

# Create our tables
db.create_all()


class MessageModelTestCase(TestCase):
    """Test the Message model."""

    def setUp(self):
        """Set up test client and sample data."""
        db.drop_all()
        db.create_all()

        # Create a test user
        self.user = User.signup(
            username="testuser",
            email="test@test.com",
            password="password",
            image_url=None
        )
        db.session.commit()

        self.client = app.test_client()

    def tearDown(self):
        """Rollback session after each test."""
        db.session.rollback()

    def test_message_creation(self):
        """Does the Message model correctly create a new message?"""
        msg = Message(
            text="This is a test message.",
            user_id=self.user.id
        )
        db.session.add(msg)
        db.session.commit()

        self.assertIsNotNone(msg.id)
        self.assertEqual(msg.text, "This is a test message.")
        self.assertEqual(msg.user_id, self.user.id)
        self.assertIsInstance(msg.timestamp, datetime)

    def test_message_missing_fields(self):
        """Does the Message model raise an error when required fields are missing?"""
        msg_missing_text = Message(user_id=self.user.id)
        msg_missing_user = Message(text="Missing user test")

        with self.assertRaises(IntegrityError):
            db.session.add(msg_missing_text)
            db.session.commit()

        with self.assertRaises(IntegrityError):
            db.session.add(msg_missing_user)
            db.session.commit()

    def test_user_relationship(self):
        """Does the `user` relationship correctly associate a Message with its User?"""
        msg = Message(
            text="Relationship test message",
            user_id=self.user.id
        )
        db.session.add(msg)
        db.session.commit()

        self.assertEqual(msg.user, self.user)
        self.assertIn(msg, self.user.messages)

    def test_timestamp_default(self):
        """Does the `timestamp` default to the current UTC time?"""
        msg = Message(
            text="Timestamp test message",
            user_id=self.user.id
        )
        db.session.add(msg)
        db.session.commit()

        now = datetime.utcnow()
        self.assertAlmostEqual(msg.timestamp, now, delta=1)  # Allow for slight differences

    def test_text_length_constraint(self):
        """Does the `text` field enforce the length constraint of 140 characters?"""
        valid_msg = Message(
            text="x" * 140,
            user_id=self.user.id
        )
        db.session.add(valid_msg)
        db.session.commit()

        self.assertEqual(len(valid_msg.text), 140)

        with self.assertRaises(IntegrityError):
            invalid_msg = Message(
                text="x" * 141,
                user_id=self.user.id
            )
            db.session.add(invalid_msg)
            db.session.commit()

    def test_cascade_on_user_delete(self):
        """Is the message properly deleted when the associated user is deleted?"""
        msg = Message(
            text="Cascade delete test",
            user_id=self.user.id
        )
        db.session.add(msg)
        db.session.commit()

        db.session.delete(self.user)
        db.session.commit()

        self.assertIsNone(Message.query.get(msg.id))