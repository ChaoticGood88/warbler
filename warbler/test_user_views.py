"""User routes tests."""

# Run these tests like:
#
#    FLASK_ENV=production python -m unittest test_user_routes.py

import os
from unittest import TestCase
from app import app, CURR_USER_KEY
from models import db, User, Message

os.environ['DATABASE_URL'] = "postgresql:///warbler-test"

db.create_all()

# Disable CSRF for easier testing
app.config['WTF_CSRF_ENABLED'] = False


class UserRoutesTestCase(TestCase):
    """Test user routes."""

    def setUp(self):
        """Set up test client and sample data."""
        db.drop_all()
        db.create_all()

        self.client = app.test_client()

        # Create test users
        self.testuser = User.signup(
            username="testuser",
            email="test@test.com",
            password="password",
            image_url=None,
        )
        self.other_user = User.signup(
            username="otheruser",
            email="other@test.com",
            password="password",
            image_url=None,
        )

        db.session.commit()

    def tearDown(self):
        """Clean up fouled transactions."""
        db.session.rollback()

    def test_list_users(self):
        """Can a user see the list of all users?"""
        with self.client as c:
            resp = c.get("/users")
            self.assertEqual(resp.status_code, 200)
            self.assertIn("testuser", str(resp.data))
            self.assertIn("otheruser", str(resp.data))

    def test_list_users_search(self):
        """Can a user search for specific users?"""
        with self.client as c:
            resp = c.get("/users?q=testuser")
            self.assertEqual(resp.status_code, 200)
            self.assertIn("testuser", str(resp.data))
            self.assertNotIn("otheruser", str(resp.data))

    def test_user_profile(self):
        """Can a user view a profile page?"""
        with self.client as c:
            resp = c.get(f"/users/{self.testuser.id}")
            self.assertEqual(resp.status_code, 200)
            self.assertIn("testuser", str(resp.data))

    def test_show_following(self):
        """Can a logged-in user see who another user is following?"""
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id

            self.testuser.following.append(self.other_user)
            db.session.commit()

            resp = c.get(f"/users/{self.testuser.id}/following")
            self.assertEqual(resp.status_code, 200)
            self.assertIn("otheruser", str(resp.data))

    def test_show_followers(self):
        """Can a logged-in user see who follows another user?"""
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id

            self.other_user.following.append(self.testuser)
            db.session.commit()

            resp = c.get(f"/users/{self.testuser.id}/followers")
            self.assertEqual(resp.status_code, 200)
            self.assertIn("otheruser", str(resp.data))

    def test_add_follow(self):
        """Can a logged-in user follow another user?"""
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id

            resp = c.post(f"/users/follow/{self.other_user.id}", follow_redirects=True)
            self.assertEqual(resp.status_code, 200)
            self.assertIn("otheruser", str(resp.data))

            self.assertIn(self.other_user, self.testuser.following)

    def test_stop_following(self):
        """Can a logged-in user stop following another user?"""
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id

            self.testuser.following.append(self.other_user)
            db.session.commit()

            resp = c.post(f"/users/stop-following/{self.other_user.id}", follow_redirects=True)
            self.assertEqual(resp.status_code, 200)
            self.assertNotIn(self.other_user, self.testuser.following)

    def test_profile_update(self):
        """Can a logged-in user update their profile?"""
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id

            resp = c.post("/users/profile", data={
                "username": "updateduser",
                "email": "updated@test.com",
                "password": "password",
                "image_url": None,
                "header_image_url": None,
                "bio": "Updated bio",
            }, follow_redirects=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("updateduser", str(resp.data))

            updated_user = User.query.get(self.testuser.id)
            self.assertEqual(updated_user.username, "updateduser")

    def test_delete_user(self):
        """Can a logged-in user delete their account?"""
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id

            resp = c.post("/users/delete", follow_redirects=True)
            self.assertEqual(resp.status_code, 200)
            self.assertIsNone(User.query.get(self.testuser.id))

    def test_show_likes(self):
        """Can a logged-in user see their liked messages?"""
        msg = Message(text="Test message", user_id=self.other_user.id)
        db.session.add(msg)
        db.session.commit()

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id

            self.testuser.likes.append(msg)
            db.session.commit()

            resp = c.get(f"/users/{self.testuser.id}/likes")
            self.assertEqual(resp.status_code, 200)
            self.assertIn("Test message", str(resp.data))

    def test_add_like(self):
        """Can a logged-in user like a message?"""
        msg = Message(text="Test message", user_id=self.other_user.id)
        db.session.add(msg)
        db.session.commit()

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id

            resp = c.post(f"/messages/{msg.id}/like", follow_redirects=True)
            self.assertEqual(resp.status_code, 200)

            self.assertIn(msg, self.testuser.likes)

"""User authentication routes tests."""

# Run these tests like:
#
#    FLASK_ENV=production python -m unittest test_auth_routes.py

import os
from unittest import TestCase
from sqlalchemy.exc import IntegrityError
from models import db, User
from app import app, CURR_USER_KEY

os.environ['DATABASE_URL'] = "postgresql:///warbler-test"

db.create_all()

# Disable CSRF for easier testing
app.config['WTF_CSRF_ENABLED'] = False


class AuthRoutesTestCase(TestCase):
    """Test user signup, login, and logout routes."""

    def setUp(self):
        """Set up test client and sample data."""
        db.drop_all()
        db.create_all()

        self.client = app.test_client()

        # Create a test user
        self.testuser = User.signup(
            username="testuser",
            email="test@test.com",
            password="password",
            image_url=None,
        )
        db.session.commit()

    def tearDown(self):
        """Clean up fouled transactions."""
        db.session.rollback()

    def test_signup(self):
        """Can a user successfully sign up?"""
        with self.client as c:
            resp = c.post("/signup", data={
                "username": "newuser",
                "password": "password",
                "email": "newuser@test.com",
                "image_url": None,
            }, follow_redirects=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("newuser", str(resp.data))

            # Verify user was added to the database
            new_user = User.query.filter_by(username="newuser").one()
            self.assertIsNotNone(new_user)
            self.assertEqual(new_user.email, "newuser@test.com")

    def test_signup_duplicate_username(self):
        """Does signup fail with a duplicate username?"""
        with self.client as c:
            resp = c.post("/signup", data={
                "username": "testuser",  # Duplicate username
                "password": "password",
                "email": "duplicate@test.com",
                "image_url": None,
            }, follow_redirects=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("Username already taken", str(resp.data))

    def test_login_valid(self):
        """Can a user log in with valid credentials?"""
        with self.client as c:
            resp = c.post("/login", data={
                "username": "testuser",
                "password": "password",
            }, follow_redirects=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("Hello, testuser!", str(resp.data))

            # Verify session is set correctly
            with c.session_transaction() as sess:
                self.assertEqual(sess[CURR_USER_KEY], self.testuser.id)

    def test_login_invalid_password(self):
        """Does login fail with an invalid password?"""
        with self.client as c:
            resp = c.post("/login", data={
                "username": "testuser",
                "password": "wrongpassword",
            }, follow_redirects=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("Invalid credentials.", str(resp.data))

            # Verify session is not set
            with c.session_transaction() as sess:
                self.assertNotIn(CURR_USER_KEY, sess)

    def test_login_invalid_username(self):
        """Does login fail with an invalid username?"""
        with self.client as c:
            resp = c.post("/login", data={
                "username": "invaliduser",
                "password": "password",
            }, follow_redirects=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("Invalid credentials.", str(resp.data))

            # Verify session is not set
            with c.session_transaction() as sess:
                self.assertNotIn(CURR_USER_KEY, sess)

    def test_logout(self):
        """Can a logged-in user log out?"""
        with self.client as c:
            # Log in the user first
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id

            resp = c.get("/logout", follow_redirects=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("Successfully logged out.", str(resp.data))

            # Verify session is cleared
            with c.session_transaction() as sess:
                self.assertNotIn(CURR_USER_KEY, sess)

    def test_logout_not_logged_in(self):
        """Does logout gracefully handle when no user is logged in?"""
        with self.client as c:
            resp = c.get("/logout", follow_redirects=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("You were not logged in.", str(resp.data))

    def test_signup_invalid_data(self):
        """Does signup fail with invalid data?"""
        with self.client as c:
            resp = c.post("/signup", data={
                "username": "",  # Invalid username
                "password": "password",
                "email": "invalid@test.com",
                "image_url": None,
            }, follow_redirects=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("This field is required.", str(resp.data))