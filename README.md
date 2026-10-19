**Sign-Language-Classification-v1.0**

Sign-Language-Classification-v1.0 là một dự án phân loại ngôn ngữ ký hiệu sử dụng các kỹ thuật học sâu và xử lý ảnh. Dự án tập trung vào việc nhận diện các ký tự trong bảng chữ cái tiếng Việt (23 ký tự không dấu) từ cử chỉ tay và một số điểm mốc trên khuôn mặt. Dự án bao gồm các công đoạn từ thu thập dữ liệu, huấn luyện mô hình CNN (dựa trên ResNet50), đến ứng dụng thời gian thực qua webcam.

<img width="700" height="862" alt="image" src="https://github.com/user-attachments/assets/c5e5c51d-ed29-48ee-890c-a12198716ef2" />

CẤU TRÚC THƯ MỤC

<img width="571" height="155" alt="image" src="https://github.com/user-attachments/assets/8239c40a-7165-4473-add0-3bba081cfa41" />


CÁC THƯ MỤC CHÍNH

data/: Chứa dữ liệu thu thập được, bao gồm các thư mục con cho từng ký tự (a, b, ..., y), mỗi thư mục chứa 50 file CSV lưu trữ landmarks của tay và mặt.

train/: Chứa các tệp mã nguồn cho việc huấn luyện mô hình, mô hình đã được huấn luyện và biểu đồ trực quan  (train_cnn_pose_keras.ipynb , vsl_cnn_pose_keras.h5, training_plot_keras.png).

process_images/: Chứa tệp Jupyter Notebook cho việc thu thập dữ liệu (capture_and_process_images.ipynb) 

run_realtime.ipynb: ứng dụng thời gian thực.

YÊU CẦU HỆ THỐNG

Phần mềm:
Python 3.8 trở lên, 
TensorFlow 2.x, 
OpenCV, 
MediaPipe, 
Pandas, NumPy, Scikit-learn, 
Matplotlib, 
Jupyter Notebook (để chạy các tệp .ipynb)


Phần cứng:
Webcam (để thu thập dữ liệu và chạy ứng dụng thời gian thực), 
GPU (khuyến nghị để huấn luyện mô hình nhanh hơn)



CÀI ĐẶT

Clone repository:
git clone https://github.com/your-repo/Sign-Language-Classification-v1.0.git
cd Sign-Language-Classification-v1.0


CÀI ĐẶT CÁC GÓI

Đảm bảo bạn đã cài đặt Python 3.8+. Bạn có thể sử dụng virtualenv hoặc conda để tạo môi trường ảo.


pip install -r requirements.txt


Nếu không có tệp requirements.txt, bạn có thể cài đặt các gói thủ công:

pip install opencv-python mediapipe pandas numpy scikit-learn tensorflow matplotlib pillow




THIẾT LẬP ĐƯỜNG DẪN

Đảm bảo rằng đường dẫn đến thư mục dữ liệu (BASE_PATH) trong các tệp mã nguồn là chính xác.

Mặc định là D:\file\project\Sign-Language-Classification-v1.0\data\anphabet.

Bạn có thể cần thay đổi đường dẫn này cho phù hợp với hệ thống của mình.



SỬ DỤNG
1. Thu thập dữ liệu

Chạy tệp capture_and_process_images.ipynb để thu thập dữ liệu landmarks cho từng ký tự.

Mỗi ký tự sẽ được thu thập 50 mẫu, lưu dưới dạng file CSV trong thư mục tương ứng (data/anphabet/<ký tự>/).

Để thu thập dữ liệu cho một ký tự cụ thể, thay đổi tham số trong hàm capture_for_letter('a') (ví dụ: 'a', 'b', ...).


2. Huấn luyện mô hình


Chạy tệp train_cnn_pose_keras.ipynb để huấn luyện mô hình CNN dựa trên ResNet50.

Dữ liệu sẽ được tải từ thư mục data/anphabet, chuyển thành heatmap, và chia thành các tập train/val/test.

Mô hình sẽ được huấn luyện với hai giai đoạn:

Giai đoạn 1: Đóng băng ResNet50 và huấn luyện các lớp tùy chỉnh.

Giai đoạn 2: Fine-tune 10 tầng cuối của ResNet50.



Mô hình đã huấn luyện sẽ được lưu vào vsl_cnn_pose_keras.h5.


3. Chạy ứng dụng thời gian thực


Chạy tệp run_realtime.ipynb để khởi động ứng dụng nhận diện ngôn ngữ ký hiệu qua webcam.

Ứng dụng sẽ hiển thị hình ảnh từ webcam và dự đoán ký tự dựa trên cử chỉ tay và khuôn mặt.

Nhấn Ctrl+C để dừng ứng dụng.


DỮ LIỆU

<img width="1024" height="657" alt="image" src="https://github.com/user-attachments/assets/925910c4-0e91-4eed-8c0d-230a4b5e6924" />


Dữ liệu bao gồm landmarks của tay (21 điểm) và mặt (10 điểm cố định) cho 23 ký tự tiếng Việt không dấu.

Mỗi ký tự có 50 mẫu, được lưu dưới dạng file CSV trong thư mục data/anphabet/<ký tự>/.

Heatmap được tạo từ landmarks và sử dụng làm đầu vào cho mô hình CNN.


MÔ HÌNH

<img width="1024" height="1024" alt="ChatGPT Image 09_36_01 3 thg 8, 2025" src="https://github.com/user-attachments/assets/a905d33c-1b2b-4a81-bc4d-9d9c0b09f90c" />



Mô hình sử dụng ResNet50 làm backbone, với các lớp tùy chỉnh bao gồm GlobalAveragePooling2D và hai lớp Dense (256 units và 23 units).

Mô hình được huấn luyện với dữ liệu heatmap và đạt độ chính xác 90% trên tập kiểm tra (cập nhật sau khi huấn luyện).


KẾT QUẢ

<img width="1200" height="400" alt="training_plot_keras" src="https://github.com/user-attachments/assets/15a2d742-499b-4b94-af1e-58fde8d8bd2a" />



Mô hình đạt độ chính xác 90% trên tập kiểm tra (cập nhật sau khi huấn luyện).

Biểu đồ huấn luyện (loss và accuracy) được lưu trong training_plot_keras.png.


GÓP Ý PHÁT TRIỂN

Chúng tôi hoan nghênh mọi đóng góp và đề xuất cải tiến cho dự án. Vui lòng gửi pull request hoặc mở issue trên GitHub để chia sẻ ý tưởng hoặc báo lỗi.

