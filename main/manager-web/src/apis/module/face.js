import { getServiceUrl } from '../api'
import RequestService from '../httpRequest'

export default {
  // 获取图片列表
  getFaceImages(callback, failCallback, deviceId = null) {
    let url = `${getServiceUrl()}/face/images`;
    if (deviceId && deviceId.trim()) {
      url += `?deviceId=${encodeURIComponent(deviceId.trim())}`;
    }

    RequestService.sendRequest()
      .url(url)
      .method('GET')
      .success((res) => {
        RequestService.clearRequestTime()
        callback(res)
      })
      .fail((err) => {
        RequestService.clearRequestTime()
        if (failCallback) {
          failCallback(err)
        }
      })
      .networkFail(() => {
        RequestService.reAjaxFun(() => {
          this.getFaceImages(callback, failCallback, deviceId)
        })
      }).send()
  }
}