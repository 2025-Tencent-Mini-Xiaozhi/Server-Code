import httpRequest from '../httpRequest'

const schedule = {
    // 获取日程列表（分页）
    getSchedulePage(params, success, fail, networkFail) {
        httpRequest.sendRequest()
            .url('/xiaozhi/schedule/page')
            .method('GET')
            .data(params)
            .success((res) => {
                if (success) success(res)
            })
            .fail((res) => {
                if (fail) fail(res)
            })
            .networkFail((res) => {
                if (networkFail) networkFail(res)
            })
            .send()
    },

    // 新增日程
    addSchedule(data, success, fail, networkFail) {
        httpRequest.sendRequest()
            .url('/xiaozhi/schedule')
            .method('POST')
            .data(data)
            .success((res) => {
                if (success) success(res)
            })
            .fail((res) => {
                if (fail) fail(res)
            })
            .networkFail((res) => {
                if (networkFail) networkFail(res)
            })
            .send()
    },

    // 修改日程
    updateSchedule(data, success, fail, networkFail) {
        httpRequest.sendRequest()
            .url('/xiaozhi/schedule')
            .method('PUT')
            .data(data)
            .success((res) => {
                if (success) success(res)
            })
            .fail((res) => {
                if (fail) fail(res)
            })
            .networkFail((res) => {
                if (networkFail) networkFail(res)
            })
            .send()
    },

    // 更新日程状态
    updateScheduleStatus(id, status, success, fail, networkFail) {
        httpRequest.sendRequest()
            .url(`/xiaozhi/schedule/${id}/status?status=${status}`)
            .method('PUT')
            .success((res) => {
                if (success) success(res)
            })
            .fail((res) => {
                if (fail) fail(res)
            })
            .networkFail((res) => {
                if (networkFail) networkFail(res)
            })
            .send()
    },

    // 删除日程
    deleteSchedule(id, success, fail, networkFail) {
        httpRequest.sendRequest()
            .url(`/xiaozhi/schedule/${id}`)
            .method('DELETE')
            .success((res) => {
                if (success) success(res)
            })
            .fail((res) => {
                if (fail) fail(res)
            })
            .networkFail((res) => {
                if (networkFail) networkFail(res)
            })
            .send()
    }
}

export default schedule