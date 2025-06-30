from loguru import logger

from widgets.notification_widget import NotificationWidget

from fabric.notifications import Notifications
from fabric.widgets.box import Box

class NotificationsContainer(Box):
    def __init__(self, **kwargs) -> None:
        super().__init__(name="popup_notifications_container", orientation="v", v_expand=True, h_expand=True,**kwargs)

        self.daemon = Notifications(on_notification_added=lambda _, id: self.handle_incoming_notification(id),
                                    on_notification_removed=lambda _, id: self.handle_removed_notification(id))

        self.notification_pos = [i for i in range(3)]

        self.notification_ids = [-1 for i in range(3)]
        self.notification_widgets = [
            NotificationWidget(transition_type="slide-down", transition_duration=200)
            for _ in range(3)
        ]
        self.notification_shown = [False for _ in range(3)]

        self.notification_queue = []

        for widget in self.notification_widgets:
            self.add(widget)

    def get_empty_widget_index(self):
        for i in self.notification_pos:
            if not self.notification_shown[i]:
                return i

        return -1

    def handle_incoming_notification(self, notification_id):
        notification = self.daemon.get_notification_from_id(notification_id)

        index = self.get_empty_widget_index()
        if index == -1:
            self.notification_queue.append(notification_id)
            return

        self.notification_widgets[index].build_from_notification(notification)
        self.notification_ids[index] = notification_id
        self.notification_shown[index] = True
        logger.error(f"notification {notification_id} added")

    def handle_removed_notification(self, notification_id):
        if notification_id not in self.notification_ids:
            if notification_id in self.notification_queue:
                self.notification_queue.remove(notification_id)
            return

        index = self.notification_ids.index(notification_id)

        self.notification_shown[index] = False
        self.notification_ids[index] = -1

        indx = self.notification_pos.index(index)
        self.notification_pos.pop(indx)
        self.notification_pos.append(index)
        self.reorder_child(self.notification_widgets[index], self.notification_widgets.__len__())

        logger.error(f"notification {notification_id} removed")

        if self.notification_queue:
            next_notification_id = self.notification_queue.pop(0)
            self.handle_incoming_notification(next_notification_id)