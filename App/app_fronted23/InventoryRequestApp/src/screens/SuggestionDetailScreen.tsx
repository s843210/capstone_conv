import React from 'react';
import {SafeAreaView, Text, View, Pressable, Alert, StyleSheet} from 'react-native';
import {SuggestionDetailScreenProps} from '../types';
import {styles} from '../styles/commonStyles';

type Props = SuggestionDetailScreenProps & {
  removeSuggestion: (suggestionId: string) => Promise<boolean>;
};

export default function SuggestionDetailScreen({navigation, route, removeSuggestion}: Props) {
  const {suggestion} = route.params;

  const handleRemove = () => {
    Alert.alert('건의사항 삭제', '이 건의사항을 삭제하시겠습니까?', [
      {text: '취소', style: 'cancel'},
      {
        text: '삭제',
        style: 'destructive',
        onPress: async () => {
          const removed = await removeSuggestion(suggestion.id);
          if (!removed) {
            Alert.alert('삭제 오류', '건의사항 삭제 중 오류가 발생했습니다.');
            return;
          }
          Alert.alert('삭제 완료', '건의사항이 삭제되었습니다.');
          navigation.reset({index: 1, routes: [{name: 'ProductList'}, {name: 'Suggestions'}]});
        },
      },
    ]);
  };

  return (
    <SafeAreaView style={styles.page}>
      <Text style={styles.title}>{suggestion.title}</Text>
      <View style={styles.card}>
        <Text style={styles.cardMeta}>작성자: {suggestion.writer}</Text>
        <Text style={styles.cardMeta}>작성일: {suggestion.createdAt}</Text>
        {!!suggestion.updatedAt && <Text style={styles.cardMeta}>수정일: {suggestion.updatedAt}</Text>}
      </View>
      <View style={styles.card}>
        <Text style={styles.cardMeta}>{suggestion.content}</Text>
      </View>

      <>
        <Pressable style={localStyles.editBtn} onPress={() => navigation.navigate('SuggestionEdit', {suggestion})}>
          <Text style={localStyles.editBtnText}>수정</Text>
        </Pressable>
        <Pressable style={localStyles.deleteBtn} onPress={handleRemove}>
          <Text style={localStyles.deleteBtnText}>삭제</Text>
        </Pressable>
      </>
    </SafeAreaView>
  );
}

const localStyles = StyleSheet.create({
  editBtn: {
    backgroundColor: '#0060AF',
    borderWidth: 1,
    borderColor: '#0060AF',
    paddingVertical: 13,
    borderRadius: 12,
    alignItems: 'center',
    marginVertical: 10,
  },
  editBtnText: {
    color: '#FFFFFF',
    fontWeight: '700',
    fontSize: 15,
  },
  deleteBtn: {
    marginTop: 4,
    backgroundColor: '#DC2626',
    borderWidth: 1,
    borderColor: '#DC2626',
    borderRadius: 12,
    paddingVertical: 12,
    alignItems: 'center',
  },
  deleteBtnText: {
    color: '#FFFFFF',
    fontWeight: '700',
    fontSize: 14,
  },
});
