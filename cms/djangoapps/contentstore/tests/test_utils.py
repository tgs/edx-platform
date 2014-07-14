""" Tests for utils. """
import collections
import copy
import mock
from datetime import datetime, timedelta
from pytz import UTC

from django.test import TestCase
from django.test.utils import override_settings

from contentstore import utils
from xmodule.modulestore import ModuleStoreEnum
from xmodule.modulestore.tests.factories import CourseFactory
from opaque_keys.edx.locations import SlashSeparatedCourseKey, Location

from xmodule.modulestore.django import modulestore


class LMSLinksTestCase(TestCase):
    """ Tests for LMS links. """
    def about_page_test(self):
        """ Get URL for about page, no marketing site """
        # default for ENABLE_MKTG_SITE is False.
        self.assertEquals(self.get_about_page_link(), "//localhost:8000/courses/mitX/101/test/about")

    @override_settings(MKTG_URLS={'ROOT': 'dummy-root'})
    def about_page_marketing_site_test(self):
        """ Get URL for about page, marketing root present. """
        with mock.patch.dict('django.conf.settings.FEATURES', {'ENABLE_MKTG_SITE': True}):
            self.assertEquals(self.get_about_page_link(), "//dummy-root/courses/mitX/101/test/about")
        with mock.patch.dict('django.conf.settings.FEATURES', {'ENABLE_MKTG_SITE': False}):
            self.assertEquals(self.get_about_page_link(), "//localhost:8000/courses/mitX/101/test/about")

    @override_settings(MKTG_URLS={'ROOT': 'http://www.dummy'})
    def about_page_marketing_site_remove_http_test(self):
        """ Get URL for about page, marketing root present, remove http://. """
        with mock.patch.dict('django.conf.settings.FEATURES', {'ENABLE_MKTG_SITE': True}):
            self.assertEquals(self.get_about_page_link(), "//www.dummy/courses/mitX/101/test/about")

    @override_settings(MKTG_URLS={'ROOT': 'https://www.dummy'})
    def about_page_marketing_site_remove_https_test(self):
        """ Get URL for about page, marketing root present, remove https://. """
        with mock.patch.dict('django.conf.settings.FEATURES', {'ENABLE_MKTG_SITE': True}):
            self.assertEquals(self.get_about_page_link(), "//www.dummy/courses/mitX/101/test/about")

    @override_settings(MKTG_URLS={'ROOT': 'www.dummyhttps://x'})
    def about_page_marketing_site_https__edge_test(self):
        """ Get URL for about page, only remove https:// at the beginning of the string. """
        with mock.patch.dict('django.conf.settings.FEATURES', {'ENABLE_MKTG_SITE': True}):
            self.assertEquals(self.get_about_page_link(), "//www.dummyhttps://x/courses/mitX/101/test/about")

    @override_settings(MKTG_URLS={})
    def about_page_marketing_urls_not_set_test(self):
        """ Error case. ENABLE_MKTG_SITE is True, but there is either no MKTG_URLS, or no MKTG_URLS Root property. """
        with mock.patch.dict('django.conf.settings.FEATURES', {'ENABLE_MKTG_SITE': True}):
            self.assertEquals(self.get_about_page_link(), None)

    @override_settings(LMS_BASE=None)
    def about_page_no_lms_base_test(self):
        """ No LMS_BASE, nor is ENABLE_MKTG_SITE True """
        self.assertEquals(self.get_about_page_link(), None)

    def get_about_page_link(self):
        """ create mock course and return the about page link """
        course_key = SlashSeparatedCourseKey('mitX', '101', 'test')
        return utils.get_lms_link_for_about_page(course_key)

    def lms_link_test(self):
        """ Tests get_lms_link_for_item. """
        course_key = SlashSeparatedCourseKey('mitX', '101', 'test')
        location = course_key.make_usage_key('vertical', 'contacting_us')
        link = utils.get_lms_link_for_item(location, False)
        self.assertEquals(link, "//localhost:8000/courses/mitX/101/test/jump_to/i4x://mitX/101/vertical/contacting_us")

        # test preview
        link = utils.get_lms_link_for_item(location, True)
        self.assertEquals(
            link,
            "//preview/courses/mitX/101/test/jump_to/i4x://mitX/101/vertical/contacting_us"
        )

        # now test with the course' location
        location = course_key.make_usage_key('course', 'test')
        link = utils.get_lms_link_for_item(location)
        self.assertEquals(link, "//localhost:8000/courses/mitX/101/test/jump_to/i4x://mitX/101/course/test")

class ExtraPanelTabTestCase(TestCase):
    """ Tests adding and removing extra course tabs. """

    def get_tab_type_dicts(self, tab_types):
        """ Returns an array of tab dictionaries. """
        if tab_types:
            return [{'tab_type': tab_type} for tab_type in tab_types.split(',')]
        else:
            return []

    def get_course_with_tabs(self, tabs=None):
        """ Returns a mock course object with a tabs attribute. """
        if tabs is None:
            tabs = []
        course = collections.namedtuple('MockCourse', ['tabs'])
        if isinstance(tabs, basestring):
            course.tabs = self.get_tab_type_dicts(tabs)
        else:
            course.tabs = tabs
        return course

    def test_add_extra_panel_tab(self):
        """ Tests if a tab can be added to a course tab list. """
        for tab_type in utils.EXTRA_TAB_PANELS.keys():
            tab = utils.EXTRA_TAB_PANELS.get(tab_type)

            # test adding with changed = True
            for tab_setup in ['', 'x', 'x,y,z']:
                course = self.get_course_with_tabs(tab_setup)
                expected_tabs = copy.copy(course.tabs)
                expected_tabs.append(tab)
                changed, actual_tabs = utils.add_extra_panel_tab(tab_type, course)
                self.assertTrue(changed)
                self.assertEqual(actual_tabs, expected_tabs)

            # test adding with changed = False
            tab_test_setup = [
                [tab],
                [tab, self.get_tab_type_dicts('x,y,z')],
                [self.get_tab_type_dicts('x,y'), tab, self.get_tab_type_dicts('z')],
                [self.get_tab_type_dicts('x,y,z'), tab]]

            for tab_setup in tab_test_setup:
                course = self.get_course_with_tabs(tab_setup)
                expected_tabs = copy.copy(course.tabs)
                changed, actual_tabs = utils.add_extra_panel_tab(tab_type, course)
                self.assertFalse(changed)
                self.assertEqual(actual_tabs, expected_tabs)

    def test_remove_extra_panel_tab(self):
        """ Tests if a tab can be removed from a course tab list. """
        for tab_type in utils.EXTRA_TAB_PANELS.keys():
            tab = utils.EXTRA_TAB_PANELS.get(tab_type)

            # test removing with changed = True
            tab_test_setup = [
                [tab],
                [tab, self.get_tab_type_dicts('x,y,z')],
                [self.get_tab_type_dicts('x,y'), tab, self.get_tab_type_dicts('z')],
                [self.get_tab_type_dicts('x,y,z'), tab]]

            for tab_setup in tab_test_setup:
                course = self.get_course_with_tabs(tab_setup)
                expected_tabs = [t for t in course.tabs if t != utils.EXTRA_TAB_PANELS.get(tab_type)]
                changed, actual_tabs = utils.remove_extra_panel_tab(tab_type, course)
                self.assertTrue(changed)
                self.assertEqual(actual_tabs, expected_tabs)

            # test removing with changed = False
            for tab_setup in ['', 'x', 'x,y,z']:
                course = self.get_course_with_tabs(tab_setup)
                expected_tabs = copy.copy(course.tabs)
                changed, actual_tabs = utils.remove_extra_panel_tab(tab_type, course)
                self.assertFalse(changed)
                self.assertEqual(actual_tabs, expected_tabs)


class CourseImageTestCase(TestCase):
    """Tests for course image URLs."""

    def test_get_image_url(self):
        """Test image URL formatting."""
        course = CourseFactory.create(org='edX', course='999')
        url = utils.course_image_url(course)
        self.assertEquals(url, '/c4x/edX/999/asset/{0}'.format(course.course_image))

    def test_non_ascii_image_name(self):
        # Verify that non-ascii image names are cleaned
        course = CourseFactory.create(course_image=u'before_\N{SNOWMAN}_after.jpg')
        self.assertEquals(
            utils.course_image_url(course),
            '/c4x/{org}/{course}/asset/before___after.jpg'.format(org=course.location.org, course=course.location.course)
        )

    def test_spaces_in_image_name(self):
        # Verify that image names with spaces in them are cleaned
        course = CourseFactory.create(course_image=u'before after.jpg')
        self.assertEquals(
            utils.course_image_url(course),
            '/c4x/{org}/{course}/asset/before_after.jpg'.format(
                org=course.location.org,
                course=course.location.course
            )
        )


class XBlockVisibilityTestCase(TestCase):
    """Tests for xblock visibility for students."""

    def setUp(self):
        self.dummy_user = ModuleStoreEnum.UserID.test
        self.past = datetime(1970, 1, 1)
        self.future = datetime.now(UTC) + timedelta(days=1)

    def test_private_unreleased_xblock(self):
        """Verifies that a private unreleased xblock is not visible"""
        vertical = self._create_xblock_with_start_date('private_unreleased', self.future)
        self.assertFalse(utils.is_xblock_visible_to_students(vertical))

    def test_private_released_xblock(self):
        """Verifies that a private released xblock is not visible"""
        vertical = self._create_xblock_with_start_date('private_released', self.past)
        self.assertFalse(utils.is_xblock_visible_to_students(vertical))

    def test_public_unreleased_xblock(self):
        """Verifies that a public (published) unreleased xblock is not visible"""
        vertical = self._create_xblock_with_start_date('public_unreleased', self.future, publish=True)
        self.assertFalse(utils.is_xblock_visible_to_students(vertical))

    def test_public_released_xblock(self):
        """Verifies that public (published) released xblock is visible"""
        vertical = self._create_xblock_with_start_date('public_released', self.past, publish=True)
        self.assertTrue(utils.is_xblock_visible_to_students(vertical))

    def test_private_no_start_xblock(self):
        """Verifies that a private xblock with no start date is not visible"""
        vertical = self._create_xblock_with_start_date('private_no_start', None)
        self.assertFalse(utils.is_xblock_visible_to_students(vertical))

    def test_public_no_start_xblock(self):
        """Verifies that a public (published) xblock with no start date is visible"""
        vertical = self._create_xblock_with_start_date('public_no_start', None, publish=True)
        self.assertTrue(utils.is_xblock_visible_to_students(vertical))

    def test_draft_released_xblock(self):
        """Verifies that a xblock with an unreleased draft and a released published version is visible"""
        vertical = self._create_xblock_with_start_date('draft_released', self.past, publish=True)

        # Create an unreleased draft version of the xblock
        vertical.start = self.future
        modulestore().update_item(vertical, self.dummy_user)

        self.assertTrue(utils.is_xblock_visible_to_students(vertical))

    def _create_xblock_with_start_date(self, name, start_date, publish=False):
        """Helper to create an xblock with a start date, optionally publishing it"""
        location = Location('edX', 'visibility', '2012_Fall', 'vertical', name)

        vertical = modulestore().create_xmodule(location)
        vertical.start = start_date
        modulestore().update_item(vertical, self.dummy_user, allow_not_found=True)

        if publish:
            modulestore().publish(location, self.dummy_user)

        return vertical


class ReleaseDateSourceTest(TestCase):
    """Tests for finding the source of an xblock's release date."""

    def setUp(self):
        self.date_one = datetime(1980, 1, 1, tzinfo=UTC)
        self.date_two = datetime(2020, 1, 1, tzinfo=UTC)

    def _create_tree(self, name, chapter_start, sequential_start, vertical_start):
        """Helper to create a tree with a chapter, sequential, and vertical"""
        locations = {
            'grandparent': Location('edX', 'date_source', name, 'chapter', 'grandparent'),
            'parent': Location('edX', 'date_source', name, 'sequential', 'parent'),
            'child': Location('edX', 'date_source', name, 'vertical', 'child'),
        }

        grandparent = modulestore().create_xmodule(locations['grandparent'], fields={
            'children': [locations['parent']],
            'start': chapter_start
        })
        modulestore().update_item(grandparent, user_id=ModuleStoreEnum.UserID.test, allow_not_found=True)

        parent = modulestore().create_xmodule(locations['parent'], fields={
            'children': [locations['child']],
            'start': sequential_start
        })
        modulestore().update_item(parent, user_id=ModuleStoreEnum.UserID.test, allow_not_found=True)

        modulestore().create_and_save_xmodule(locations['child'], user_id=ModuleStoreEnum.UserID.test, fields={
            'start': vertical_start
        })

        return locations

    def _verify_release_date_source(self, location, expected_source_location):
        """Helper to verify that the release date source of a given item matches the expected source"""
        source = utils.find_release_date_source(modulestore().get_item(location))
        expected_source = modulestore().get_item(expected_source_location)
        self.assertEqual(source.location, expected_source.location)
        self.assertEqual(source.start, expected_source.start)

    def test_chapter_source(self):
        """Tests an xblock's release date being set by its grandparent chapter"""
        locations = self._create_tree('chapter_source', self.date_one, self.date_one, self.date_one)
        self._verify_release_date_source(locations['child'], locations['grandparent'])

    def test_sequential_source(self):
        """Tests an xblock's release date being set by its parent sequential"""
        locations = self._create_tree('sequential_source', self.date_one, self.date_two, self.date_two)
        self._verify_release_date_source(locations['child'], locations['parent'])
