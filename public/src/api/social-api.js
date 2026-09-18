/** Friends, messages and notifications. */

import { apiDelete, apiGet, apiPost } from './client.js';

export const fetchFriends = () => apiGet('/friends');
export const sendFriendRequest = (userId) => apiPost('/friends/requests', { user_id: userId });
export const acceptFriendRequest = (requestId) => apiPost(`/friends/requests/${requestId}/accept`);
export const removeFriendRequest = (requestId) => apiDelete(`/friends/requests/${requestId}`);
export const unfriend = (userId) => apiDelete(`/friends/${userId}`);

export const fetchConversations = () => apiGet('/messages');
export const fetchThread = (userId) => apiGet(`/messages/${userId}`);
export const sendMessage = (userId, body) => apiPost(`/messages/${userId}`, { body });

export const fetchNotifications = () => apiGet('/notifications');
/** Mark one notification read, or all of them when no id is given. */
export const markNotificationsRead = (id) => apiPost('/notifications/read', id === undefined ? {} : { id });
