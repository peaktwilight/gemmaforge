TfLiteStatus ResizeOutputTensor(TfLiteContext* context,
                                const TfLiteTensor* data,
                                const TfLiteTensor* segment_ids,
                                TfLiteTensor* output) {
  // Segment ids should be of same cardinality as first input dimension and they
  // should be increasing by at most 1, from 0 (e.g., [0, 0, 1, 2, 3] is valid)
  const int segment_id_size = segment_ids->dims->data[0];
  TF_LITE_ENSURE_EQ(context, segment_id_size, data->dims->data[0]);
  int previous_segment_id = -1;
  for (int i = 0; i < segment_id_size; i++) {
    const int current_segment_id = GetTensorData<int32_t>(segment_ids)[i];
    if (i == 0) {
      TF_LITE_ENSURE_EQ(context, current_segment_id, 0);
    } else {
      int delta = current_segment_id - previous_segment_id;
      TF_LITE_ENSURE(context, delta == 0 || delta == 1);
    }
    previous_segment_id = current_segment_id;
  }

  const int max_index = previous_segment_id;

  const int data_rank = NumDimensions(data);
  TfLiteIntArray* output_shape = TfLiteIntArrayCreate(NumDimensions(data));
  output_shape->data[0] = max_index + 1;
  for (int i = 1; i < data_rank; ++i) {
    output_shape->data[i] = data->dims->data[i];
  }
  return context->ResizeTensor(context, output, output_shape);
}
